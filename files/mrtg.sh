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

get_device_name() {
  local community=$1 host=$2 port=$3 version=$4
  local snmp_ver name
  snmp_ver=$(get_snmp_version "${version}")
  name=$(snmpwalk -Oqv -v"${snmp_ver}" -c "${community}" "${host}:${port}" .1.3.6.1.2.1.1.5)
  trim "${name:-${host}}" | tr '[:upper:]' '[:lower:]' | tr '[:space:]' '_'
}

generate_cfg() {
  local community=$1 host=$2 version=$3 port=$4 name=$5
  /usr/bin/cfgmaker \
    --ifref=name \
    --global "WorkDir: ${WEBDIR}" \
    --global "Options[_]: ${GRAPHOPTIONS}" \
    --global "EnableIPv6: ${ENABLE_V6}" \
    --global "LogFormat: rrdtool" \
    ${CFGMAKEROPTIONS} \
    --snmp-options=:"${port}"::::"${version//c/}" \
    --output="${MRTGDIR}/conf.d/${name}.cfg" "${community}@${host}"
}

process_host() {
  local asset=$1
  local community host version port name
  read -r community host version port < <(echo "${asset//:/ }")
  port=${port:-161}
  version=$(get_snmp_version "${version}")
  name=$(get_device_name "${community}" "${host}" "${port}" "${version}")

  if [[ ! -f "${MRTGDIR}/conf.d/${name}.cfg" ]]; then
    generate_cfg "${community}" "${host}" "${version}" "${port}" "${name}"
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
  NAME=$(get_device_name "${COMMUNITY}" "${HOST}" "${PORT}" "${VERSION}")

  if [[ ! -f "${MRTGDIR}/conf.d/${NAME}.cfg" ]]; then
    generate_cfg "${COMMUNITY}" "${HOST}" "${VERSION}" "${PORT}" "${NAME}"
  fi
fi

# Clean font cache
chmod 755 /var/cache/fontconfig
rm -rf /var/cache/fontconfig/*
fc-cache -f

run_mrtg
regenerate_html
start_services
