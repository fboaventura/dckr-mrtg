#!/bin/bash -e

MRTGDIR=${MRTGDIR:-"/etc/mrtg"}
WEBDIR=${WEBDIR:-"/mrtg/html"}
MRTGCFG=${MRTGDIR}/mrtg.cfg
PATHPREFIX=${PATHPREFIX:-""}

usermod -u ${USERID} lighttpd
groupmod -g ${GROUPID} lighttpd

[[ ! -d "${MRTGDIR}" ]] && mkdir -p ${MRTGDIR}
[[ ! -d "${WEBDIR}" ]] && mkdir -p ${WEBDIR}

if [ -n "${HOSTS}" ]; then
    hosts=$(echo ${HOSTS} | tr '[,;]' ' ')
    for asset in ${hosts}; do
        read -r COMMUNITY HOST VERSION PORT < <(echo ${asset} | sed -e 's/:/ /g')
        # COMMUNITY=$(echo $asset | cut -d: -f1)
        # HOST=$(echo $asset | cut -d: -f2)
        if [[ "${VERSION}" -eq "2" || -z "${VERSION}" ]]; then _snmp_ver="2c"; else _snmp_ver=${VERSION}; fi
        NAME=$(snmpwalk -Oqv -v${_snmp_ver} -c ${COMMUNITY} ${HOST}:${PORT:-"161"} .1.3.6.1.2.1.1.5)
        if [ -z "${NAME}" ]; then
            NAME="${HOST}"
        fi
        [[ ! -f "${MRTGDIR}/conf.d/${NAME}.cfg" ]] && /usr/bin/cfgmaker \
            --ifref=name \
            --global "WorkDir: ${WEBDIR}" \
            --global "Options[_]: growright, bits" \
            --global "EnableIPv6: ${ENABLE_V6}" \
            --global "LogFormat: rrdtool" \
            --snmp-options=:${PORT:-"161"}::::${VERSION:-"2"} \
            --output=${MRTGDIR}/conf.d/${NAME}.cfg "${COMMUNITY}@${HOST}"
    done
else
    COMMUNITY=${1:-"public"}
    HOST=${2:-"localhost"}
    VERSION=${3:-"2"}
    PORT=${4:-"161"}
    if [[ "${VERSION}" -eq "2" || -z "${VERSION}" ]]; then _snmp_ver="2c"; else _snmp_ver=${VERSION}; fi
    NAME=$(snmpwalk -Oqv -v${_snmp_ver} -c ${COMMUNITY} ${HOST}:${PORT} .1.3.6.1.2.1.1.5)
    if [ -z "${NAME}" ]; then
        NAME="${HOST}"
    fi
    [[ ! -f "${MRTGDIR}/conf.d/${NAME}.cfg" ]] && /usr/bin/cfgmaker \
            --ifref=name \
            --global "Options[_]: growright, bits" \
            --global "EnableIPv6: ${ENABLE_V6}" \
            --global "LogFormat: rrdtool" \
            --snmp-options=:${PORT}::::${VERSION} \
            --output=${MRTGDIR}/conf.d/${NAME}.cfg "${COMMUNITY}@${HOST}"
fi

env LANG=C /usr/bin/mrtg ${MRTGCFG}
sleep 2
env LANG=C /usr/bin/mrtg ${MRTGCFG}
sleep 2
env LANG=C /usr/bin/mrtg ${MRTGCFG}

# Only run indexmaker when regeneration is wanted.
if [ $REGENERATEHTML == "yes" ]; then
  echo "Regenerating HTML"
  if [ -e "${WEBDIR}/index.html" ]; then
     mv -f "${WEBDIR}/index.html" "${WEBDIR}/index.old"
  fi
  /usr/bin/indexmaker --columns=1 ${MRTGCFG} -rrdviewer=${PATHPREFIX}/cgi-bin/14all.cgi --icondir=/ --prefix=${PATHPREFIX}/ $INDEXMAKEROPTIONS > ${WEBDIR}/index.html
fi


chown -R lighttpd:lighttpd ${WEBDIR}

/usr/sbin/lighttpd -f /etc/lighttpd/lighttpd.conf -D &
HTTPID=$!

/usr/sbin/crond -f -L /proc/self/fd/1 -l debug &
CRONDID=$!

trap "kill ${HTTPID} ${CRONDID}" SIGINT SIGHUP SIGTERM SIGQUIT EXIT
wait
