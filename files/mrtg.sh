#!/bin/bash -ex

# Default configurations
MIBSDIR=${MIBSDIR:-"/mrtg/mibs"}
MRTGDIR=${MRTGDIR:-"/etc/mrtg"}
WEBDIR=${WEBDIR:-"/mrtg/html"}
MRTGCFG=${MRTGDIR}/mrtg.cfg
CFGMAKEROPTIONS=${CFGMAKEROPTIONS:-""}
ENABLE_V6=${ENABLE_V6:-"no"}
GRAPHOPTIONS=${GRAPHOPTIONS:-"growright, bits"}
HOSTS=${HOSTS:-""}
INDEXMAKEROPTIONS=${INDEXMAKEROPTIONS:-""}
MRTG_COLUMNS=${MRTG_COLUMNS:-"2"}
PATHPREFIX=${PATHPREFIX:-""}
REGENERATEHTML=${REGENERATEHTML:-"yes"}

whoami() {
  if [ "$(id -u)" -eq 0 ]; then
    echo "Running as root"
  else
    echo "Running as non-root user"
  fi
}
whoami

trim() {
  local var="$*"
  # remove leading whitespace characters
  var="${var#"${var%%[![:space:]]*}"}"
  # remove trailing whitespace characters
  var="${var%"${var##*[![:space:]]}"}"
  printf '%s' "$var"
}

# Helper Functions
setup_directories() {
  mkdir -p "${MRTGDIR}" "${WEBDIR}" "${MIBSDIR}"
  if [[ -d "/mrtg/icons" ]]; then
    echo "Copying icons from /mrtg/icons to ${WEBDIR}/icons"
    if [[ ! -d "${WEBDIR}/icons" ]]; then
      cp -Rv /mrtg/icons "${WEBDIR}/"
    else
      echo "Warning: Icon directory already exists. Skipping copy."
    fi
  else
    echo "Warning: Source directory /mrtg/icons does not exist. Skipping icon copy."
  fi
}

configure_icon_dir() {
  local icon_dir="${PATHPREFIX:+${PATHPREFIX}/}icons"
  echo "IconDir: ${icon_dir}" >"${MRTGDIR}/conf.d/001-IconDir.cfg"
}

load_mibs() {
  if [ -n "$(ls -A "${MIBSDIR}")" ]; then
    echo "Loading MIBs from ${MIBSDIR}"
    local mibs_files
    mibs_files=$(find "${MIBSDIR}" -type f -print0 | xargs -0 echo | tr ' ' ',')
    echo "LoadMIBs: ${mibs_files}" >"${MRTGDIR}/conf.d/002-LoadMIBs.cfg"
    echo "MIBS: ${mibs_files}"
  fi
}

get_snmp_version() {
  [[ "$1" == "2" || -z "$1" ]] && echo "2c" || echo "$1"
}

normalize_privproto() {
  case "${1,,}" in
    aes|aes128|aescfb128) echo "aescfb128" ;;
    aes192|aescfb192)     echo "aescfb192" ;;
    aes256|aescfb256)     echo "aescfb256" ;;
    3des|3desede)         echo "3desede"   ;;
    *)                    echo "${1,,}"    ;;
  esac
}

get_device_name() {
  local community=$1 host=$2 port=$3 version=$4
  local authproto=$5 authpass=$6 privproto=$7 privpass=$8 seclevel=$9
  local snmp_ver name
  snmp_ver=$(get_snmp_version "${version}")

  if [[ "${snmp_ver}" == "3" ]]; then
    name=$(snmpwalk -Oqv -v3 \
      -u "${community}" \
      -l "${seclevel:-noAuthNoPriv}" \
      ${authproto:+-a "${authproto}"} \
      ${authpass:+-A "${authpass}"} \
      ${privproto:+-x "${privproto}"} \
      ${privpass:+-X "${privpass}"} \
      "${host}:${port}" .1.3.6.1.2.1.1.5)
  else
    name=$(snmpwalk -Oqv -v"${snmp_ver}" -c "${community}" "${host}:${port}" .1.3.6.1.2.1.1.5)
  fi

  trim "${name:-${host}}" | tr '[:upper:]' '[:lower:]' | tr '[:space:]' '_'
}

generate_cfg() {
  local community=$1 host=$2 version=$3 port=$4 name=$5
  local authproto=$6 authpass=$7 privproto=$8 privpass=$9 seclevel=${10}

  if [[ "${version//c/}" == "3" ]]; then
    local norm_privproto
    norm_privproto=$(normalize_privproto "${privproto}")
    /usr/bin/cfgmaker \
      --ifref=name \
      --global "WorkDir: ${WEBDIR}" \
      --global "Options[_]: ${GRAPHOPTIONS}" \
      --global "EnableIPv6: ${ENABLE_V6}" \
      --global "LogFormat: rrdtool" \
      ${CFGMAKEROPTIONS} \
      --snmp-options=:"${port}"::::3 \
      --enablesnmpv3 \
      --username="${community}" \
      ${authproto:+--authprotocol="${authproto,,}"} \
      ${authpass:+--authpassword="${authpass}"} \
      ${norm_privproto:+--privprotocol="${norm_privproto}"} \
      ${privpass:+--privpassword="${privpass}"} \
      --output="${MRTGDIR}/conf.d/${name}.cfg" "${community}@${host}"
  else
    /usr/bin/cfgmaker \
      --ifref=name \
      --global "WorkDir: ${WEBDIR}" \
      --global "Options[_]: ${GRAPHOPTIONS}" \
      --global "EnableIPv6: ${ENABLE_V6}" \
      --global "LogFormat: rrdtool" \
      ${CFGMAKEROPTIONS} \
      --snmp-options=:"${port}"::::"${version//c/}" \
      --output="${MRTGDIR}/conf.d/${name}.cfg" "${community}@${host}"
  fi
}

check_host_alive() {
  local host=$1
  local port=$2

  if ! nc -vuz "${host}" "${port}" 2>/dev/null; then
    echo "Host ${host}:${port} is not reachable. Skipping."
    return 1
  fi
  return 0
}

process_host() {
  local asset=$1
  local community host version port authproto authpass privproto privpass seclevel name
  IFS=':' read -r community host version port authproto authpass privproto privpass <<< "${asset}"
  port=${port:-161}

  if ! check_host_alive "${host}" "${port}"; then
    return
  fi

  version=$(get_snmp_version "${version}")

  if [[ "${version}" == "3" ]]; then
    if [[ -n "${privpass}" ]]; then
      seclevel="authPriv"
    elif [[ -n "${authpass}" ]]; then
      seclevel="authNoPriv"
    else
      seclevel="noAuthNoPriv"
    fi
    name=$(get_device_name "${community}" "${host}" "${port}" "${version}" \
      "${authproto}" "${authpass}" "${privproto}" "${privpass}" "${seclevel}")
    if [[ ! -f "${MRTGDIR}/conf.d/${name}.cfg" ]]; then
      generate_cfg "${community}" "${host}" "${version}" "${port}" "${name}" \
        "${authproto}" "${authpass}" "${privproto}" "${privpass}" "${seclevel}"
    fi
  else
    name=$(get_device_name "${community}" "${host}" "${port}" "${version}")
    if [[ ! -f "${MRTGDIR}/conf.d/${name}.cfg" ]]; then
      generate_cfg "${community}" "${host}" "${version}" "${port}" "${name}"
    fi
  fi
}

run_mrtg() {
  env LANG=C /usr/bin/mrtg "${MRTGCFG}" || true
  sleep 2
  env LANG=C /usr/bin/mrtg "${MRTGCFG}" || true
  sleep 2
  env LANG=C /usr/bin/mrtg "${MRTGCFG}" || true
}

regenerate_html() {
  if [ "${REGENERATEHTML}" == "yes" ]; then
    echo "Regenerating HTML"
    [ -e "${WEBDIR}/index.html" ] && mv -f "${WEBDIR}/index.html" "${WEBDIR}/index.old"
    /usr/bin/indexmaker "${MRTGCFG}" \
      --columns="${MRTG_COLUMNS}" \
      --rrdviewer="${PATHPREFIX}/cgi-bin/14all.cgi" \
      --prefix="${PATHPREFIX}/" \
      ${INDEXMAKEROPTIONS} \
      --output="${WEBDIR}/index.html"
    echo "HTML regenerated"
  fi
}

start_services() {
  /usr/bin/supervisord -c /etc/supervisord.conf -n
}

# Main Script Execution
setup_directories
configure_icon_dir
load_mibs

if [ -n "${HOSTS}" ]; then
  for asset in $(echo "${HOSTS}" | tr ',;' ' '); do
    process_host "${asset}"
  done
else
  COMMUNITY=${1:-"public"}
  HOST=${2:-"localhost"}
  VERSION=${3:-"2"}
  PORT=${4:-"161"}
  AUTHPROTO=${5:-""}
  AUTHPASS=${6:-""}
  PRIVPROTO=${7:-""}
  PRIVPASS=${8:-""}
  if ! check_host_alive "${HOST}" "${PORT}"; then
    echo "Host ${HOST}:${PORT} is not reachable. Exiting."
    exit 1
  fi
  VERSION=$(get_snmp_version "${VERSION}")

  if [[ "${VERSION}" == "3" ]]; then
    if [[ -n "${PRIVPASS}" ]]; then
      SECLEVEL="authPriv"
    elif [[ -n "${AUTHPASS}" ]]; then
      SECLEVEL="authNoPriv"
    else
      SECLEVEL="noAuthNoPriv"
    fi
    NAME=$(get_device_name "${COMMUNITY}" "${HOST}" "${PORT}" "${VERSION}" \
      "${AUTHPROTO}" "${AUTHPASS}" "${PRIVPROTO}" "${PRIVPASS}" "${SECLEVEL}")
    if [[ ! -f "${MRTGDIR}/conf.d/${NAME}.cfg" ]]; then
      generate_cfg "${COMMUNITY}" "${HOST}" "${VERSION}" "${PORT}" "${NAME}" \
        "${AUTHPROTO}" "${AUTHPASS}" "${PRIVPROTO}" "${PRIVPASS}" "${SECLEVEL}"
    fi
  else
    NAME=$(get_device_name "${COMMUNITY}" "${HOST}" "${PORT}" "${VERSION}")
    if [[ ! -f "${MRTGDIR}/conf.d/${NAME}.cfg" ]]; then
      generate_cfg "${COMMUNITY}" "${HOST}" "${VERSION}" "${PORT}" "${NAME}"
    fi
  fi
fi

# Clean font cache
chmod 755 /var/cache/fontconfig
rm -rf /var/cache/fontconfig/*
fc-cache -f

run_mrtg
regenerate_html
start_services
