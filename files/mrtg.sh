#!/bin/bash -e

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

usermod -u "${USERID}" lighttpd >/dev/null 2>&1
groupmod -g "${GROUPID}" lighttpd >/dev/null 2>&1

[[ ! -d "${MRTGDIR}" ]] && mkdir -p "${MRTGDIR}"
[[ ! -d "${WEBDIR}" ]] && mkdir -p "${WEBDIR}"
[[ ! -d "${MIBSDIR}" ]] && mkdir -p "${MIBSDIR}"
[[ ! -d "${WEBDIR}/icons" ]] && cp -R /mrtg/icons "${WEBDIR}"/

if [ -n "${PATHPREFIX}" ]; then
    echo "IconDir: ${PATHPREFIX}/icons" > "${MRTGDIR}/conf.d/001-IconDir.cfg"
else
    echo "IconDir: /icons" > "${MRTGDIR}/conf.d/001-IconDir.cfg"
fi

if [ -n "$(ls -A "${MIBSDIR}")" ]; then
  echo "Loading MIBs from ${MIBSDIR}"
  _MIBS_FILES=$(find "${MIBSDIR}" -type f -print0 | xargs -0 echo | tr ' ' ',')
  echo "LoadMIBs: ${_MIBS_FILES}" > "${MRTGDIR}/conf.d/002-LoadMIBs.cfg"
  echo "MIBS: ${_MIBS_FILES}"
fi

if [ -n "${HOSTS}" ]; then
    hosts=$(echo "${HOSTS}" | tr ',;' ' ')
    for asset in ${hosts}; do
        read -r COMMUNITY HOST VERSION PORT < <(echo "${asset//:/ }")
        if [[ "${VERSION}" -eq "2" || -z "${VERSION}" ]]; then _snmp_ver="2c"; else _snmp_ver=${VERSION}; fi
        NAME=$(snmpwalk -Oqv -v"${_snmp_ver}" -c "${COMMUNITY}" "${HOST}":"${PORT:-"161"}" .1.3.6.1.2.1.1.5)
        if [ -z "${NAME}" ]; then
            NAME="${HOST}"
        fi
        if [[ ! -f "${MRTGDIR}/conf.d/${NAME}.cfg" ]]; then
          if [ -n "${CFGMAKEROPTIONS}" ]; then
            # shellcheck disable=SC2086
            echo /usr/bin/cfgmaker \
                --ifref=name \
                --global "WorkDir: ${WEBDIR}" \
                --global "Options[_]: ${GRAPHOPTIONS}" \
                --global "EnableIPv6: ${ENABLE_V6}" \
                --global "LogFormat: rrdtool" \
                ${CFGMAKEROPTIONS} \
                --snmp-options=:"${PORT}"::::"${VERSION}" \
                --output="${MRTGDIR}/conf.d/${NAME}.cfg" "${COMMUNITY}@${HOST}"
            # shellcheck disable=SC2086
            /usr/bin/cfgmaker \
                --ifref=name \
                --global "WorkDir: ${WEBDIR}" \
                --global "Options[_]: ${GRAPHOPTIONS}" \
                --global "EnableIPv6: ${ENABLE_V6}" \
                --global "LogFormat: rrdtool" \
                ${CFGMAKEROPTIONS} \
                --snmp-options=:"${PORT}"::::"${VERSION}" \
                --output="${MRTGDIR}/conf.d/${NAME}.cfg" "${COMMUNITY}@${HOST}"
          else
            echo /usr/bin/cfgmaker \
                --ifref=name \
                --global "WorkDir: ${WEBDIR}" \
                --global "Options[_]: ${GRAPHOPTIONS}" \
                --global "EnableIPv6: ${ENABLE_V6}" \
                --global "LogFormat: rrdtool" \
                --snmp-options=:"${PORT}"::::"${VERSION}" \
                --output="${MRTGDIR}/conf.d/${NAME}.cfg" "${COMMUNITY}@${HOST}"
            /usr/bin/cfgmaker \
                --ifref=name \
                --global "WorkDir: ${WEBDIR}" \
                --global "Options[_]: ${GRAPHOPTIONS}" \
                --global "EnableIPv6: ${ENABLE_V6}" \
                --global "LogFormat: rrdtool" \
                --snmp-options=:"${PORT}"::::"${VERSION}" \
                --output="${MRTGDIR}/conf.d/${NAME}.cfg" "${COMMUNITY}@${HOST}"
          fi
        fi
    done
else
    COMMUNITY=${1:-"public"}
    HOST=${2:-"localhost"}
    VERSION=${3:-"2"}
    PORT=${4:-"161"}
    if [[ "${VERSION}" -eq "2" || -z "${VERSION}" ]]; then _snmp_ver="2c"; else _snmp_ver=${VERSION}; fi
    NAME=$(snmpwalk -Oqv -v"${_snmp_ver}" -c "${COMMUNITY}" "${HOST}":"${PORT}" .1.3.6.1.2.1.1.5 | tr '[:upper:]' '[:lower:]' | tr '[:space:]' '_')
    if [ -z "${NAME}" ]; then
        NAME="${HOST}"
    fi
    if [[ ! -f "${MRTGDIR}/conf.d/${NAME}.cfg" ]]; then
      if [ -n "${CFGMAKEROPTIONS}" ]; then
        # shellcheck disable=SC2086
        /usr/bin/cfgmaker \
            --ifref=name \
            --global "WorkDir: ${WEBDIR}" \
            --global "Options[_]: ${GRAPHOPTIONS}" \
            --global "EnableIPv6: ${ENABLE_V6}" \
            --global "LogFormat: rrdtool" \
            ${CFGMAKEROPTIONS} \
            --snmp-options=:"${PORT}"::::"${VERSION}" \
            --output="${MRTGDIR}/conf.d/${NAME}.cfg" "${COMMUNITY}@${HOST}"
      else
        /usr/bin/cfgmaker \
            --ifref=name \
            --global "WorkDir: ${WEBDIR}" \
            --global "Options[_]: ${GRAPHOPTIONS}" \
            --global "EnableIPv6: ${ENABLE_V6}" \
            --global "LogFormat: rrdtool" \
            --snmp-options=:"${PORT}"::::"${VERSION}" \
            --output="${MRTGDIR}/conf.d/${NAME}.cfg" "${COMMUNITY}@${HOST}"
      fi
    fi
fi

# Force font cache clean-up to avoid fontconfig errors
chmod 755 /var/cache/fontconfig
rm -rf /var/cache/fontconfig/*
fc-cache -f

env LANG=C /usr/bin/mrtg "${MRTGCFG}"
sleep 2
env LANG=C /usr/bin/mrtg "${MRTGCFG}"
sleep 2
env LANG=C /usr/bin/mrtg "${MRTGCFG}"

# Only run indexmaker when regeneration is wanted.
if [ "${REGENERATEHTML}" == "yes" ]; then
  echo "Regenerating HTML"
  if [ -e "${WEBDIR}/index.html" ]; then
     mv -f "${WEBDIR}/index.html" "${WEBDIR}/index.old"
  fi
  if [ -n "${INDEXMAKEROPTIONS}" ]; then
    # shellcheck disable=SC2086
    echo /usr/bin/indexmaker "${MRTGCFG}" --columns="${MRTG_COLUMNS}" --rrdviewer="${PATHPREFIX}/cgi-bin/14all.cgi" --prefix="${PATHPREFIX}/" ${INDEXMAKEROPTIONS} --output="${WEBDIR}/index.html"
    # shellcheck disable=SC2086
    /usr/bin/indexmaker "${MRTGCFG}" --columns="${MRTG_COLUMNS}" --rrdviewer="${PATHPREFIX}/cgi-bin/14all.cgi" --prefix="${PATHPREFIX}/" ${INDEXMAKEROPTIONS} --output="${WEBDIR}/index.html"
  else
    echo /usr/bin/indexmaker "${MRTGCFG}" --columns="${MRTG_COLUMNS}" --rrdviewer="${PATHPREFIX}/cgi-bin/14all.cgi" --prefix="${PATHPREFIX}/" --output="${WEBDIR}/index.html"
    /usr/bin/indexmaker "${MRTGCFG}" --columns="${MRTG_COLUMNS}" --rrdviewer="${PATHPREFIX}/cgi-bin/14all.cgi" --prefix="${PATHPREFIX}/" --output="${WEBDIR}/index.html"
  fi
  echo "HTML regenerated"
fi


chown -R lighttpd:lighttpd "${WEBDIR}"

/usr/sbin/lighttpd -f /etc/lighttpd/lighttpd.conf -D &
HTTPID=$!

/usr/sbin/crond -f -L /proc/self/fd/1 -l debug &
CRONDID=$!

trap "kill ${HTTPID} ${CRONDID}" SIGINT SIGHUP SIGTERM SIGQUIT EXIT
wait
