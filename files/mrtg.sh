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
MAX_PARALLEL_HOSTS=${MAX_PARALLEL_HOSTS:-5}
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
  local community host version port name

  # Disable exit on error for this function (inherited from -e flag)
  set +e

  read -r community host version port < <(echo "${asset//:/ }")
  port=${port:-161}

  echo "Processing host: ${asset}"

  if ! check_host_alive "${host}" "${port}"; then
    echo "Skipping host ${host}:${port} - not reachable"
    return 0
  fi

  version=$(get_snmp_version "${version}")
  name=$(get_device_name "${community}" "${host}" "${port}" "${version}")

  echo "Device name resolved: ${name}"

  if [[ ! -f "${MRTGDIR}/conf.d/${name}.cfg" ]]; then
    echo "Generating config for ${name}"
    generate_cfg "${community}" "${host}" "${version}" "${port}" "${name}"
    echo "Config generated for ${name}"
  else
    echo "Config already exists for ${name}"
  fi

  # Re-enable exit on error
  set -e
  return 0
}

process_hosts_parallel() {
  local max_parallel=${MAX_PARALLEL_HOSTS:-5}
  local pids=()
  local count=0
  local total=0

  echo "Starting parallel host processing..."

  for asset in $(echo "${HOSTS}" | tr ',;' ' '); do
    # Run process_host in background with set +e to prevent exit on error
    (
      set +e
      process_host "${asset}"
      exit 0
    ) &
    pids+=($!)
    ((total++))
    ((count++))

    # If we've reached max parallel processes, wait for one to finish
    if [ ${count} -ge ${max_parallel} ]; then
      # Wait for any job to complete
      if wait -n 2>/dev/null; then
        ((count--))
      else
        # wait -n not supported, fall back to waiting for all
        for pid in "${pids[@]}"; do
          wait "${pid}" 2>/dev/null || true
        done
        count=0
        pids=()
      fi
    fi
  done

  # Wait for all remaining background jobs to complete
  echo "Waiting for remaining ${count} background jobs to complete..."
  for pid in "${pids[@]}"; do
    wait "${pid}" 2>/dev/null || true
  done

  echo "All ${total} hosts processed"
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
  echo "Processing hosts in parallel (max ${MAX_PARALLEL_HOSTS} concurrent)"
  process_hosts_parallel
else
  COMMUNITY=${1:-"public"}
  HOST=${2:-"localhost"}
  VERSION=${3:-"2"}
  PORT=${4:-"161"}
  if ! check_host_alive "${HOST}" "${PORT}"; then
    echo "Host ${HOST}:${PORT} is not reachable. Exiting."
    exit 1
  fi
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
