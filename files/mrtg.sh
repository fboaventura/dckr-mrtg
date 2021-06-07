#!/bin/bash -e

MRTGDIR=${MRTGDIR:-"/etc/mrtg"}
WEBDIR=${WEBDIR:-"/mrtg/html"}
MRTGCFG=${MRTGDIR}/mrtg.cfg

[[ ! -d "${MRTGDIR}" ]] && mkdir -p ${MRTGDIR}
[[ ! -d "${WEBDIR}" ]] && mkdir -p ${WEBDIR}

if [ -n "${HOSTS}" ]; then
    hosts=$(echo ${HOSTS} | tr '[,;]' ' ')
    for asset in ${hosts}; do
        read -r COMMUNITY HOST VERSION < <(echo ${asset} | sed -e 's/:/ /g')
        # COMMUNITY=$(echo $asset | cut -d: -f1)
        # HOST=$(echo $asset | cut -d: -f2)
        if [[ "${VERSION}" -eq "2" || -z "${VERSION}" ]]; then _snmp_ver="2c"; else _snmp_ver=${VERSION}; fi
        NAME=$(snmpwalk -Oqv -v${_snmp_ver} -c ${COMMUNITY} ${HOST} .1.3.6.1.2.1.1.5)
        if [ -z "${NAME}" ]; then
            NAME="${HOST}"
        fi
        [[ ! -f "${MRTGDIR}/conf.d/${NAME}.cfg" ]] && /usr/bin/cfgmaker \
            --ifref=name \
            --global "WorkDir: ${WEBDIR}" \
            --global "Options[_]: growright, bits" \
            --global "EnableIPv6: ${ENABLE_V6}" \
            --global "LogFormat: rrdtool" \
            --snmp-options=:::::${VERSION:-2} \
            --output=${MRTGDIR}/conf.d/${NAME}.cfg "${COMMUNITY}@${HOST}"
    done
else
    COMMUNITY=${1:-"public"}
    HOST=${2:-"localhost"}
    VERSION=${3:-"2"}
    if [[ "${VERSION}" -eq "2" || -z "${VERSION}" ]]; then _snmp_ver="2c"; else _snmp_ver=${VERSION}; fi
    NAME=$(snmpwalk -Oqv -v${_snmp_ver} -c ${COMMUNITY} ${HOST} .1.3.6.1.2.1.1.5)
    if [ -z "${NAME}" ]; then
        NAME="${HOST}"
    fi
    [[ ! -f "${MRTGDIR}/conf.d/${NAME}.cfg" ]] && /usr/bin/cfgmaker \
            --ifref=name \
            --global "Options[_]: growright, bits" \
            --global "EnableIPv6: ${ENABLE_V6}" \
            --global "LogFormat: rrdtool" \
            --snmp-options=:::::${VERSION:-2} \
            --output=${MRTGDIR}/conf.d/${NAME}.cfg "${COMMUNITY}@${HOST}"
fi

env LANG=C /usr/bin/mrtg ${MRTGCFG}
sleep 2
env LANG=C /usr/bin/mrtg ${MRTGCFG}
sleep 2
env LANG=C /usr/bin/mrtg ${MRTGCFG}
/usr/bin/indexmaker --columns=1 ${MRTGCFG} > ${WEBDIR}/index.html
chown -R lighttpd:lighttpd ${WEBDIR}

# /usr/sbin/nginx &
# NGINXID=$!

/usr/sbin/lighttpd -f /etc/lighttpd/lighttpd.conf &
HTTPID=$!

/usr/sbin/crond -f -L /proc/self/fd/1 -l debug &
CRONDID=$!

trap "kill ${HTTPID} ${CRONDID}" SIGINT SIGHUP SIGTERM SIGQUIT EXIT
wait
