#!/bin/sh -e

MRTGDIR=/etc/mrtg
WEBDIR=/usr/share/nginx/html
MRTGCFG=${MRTGDIR}/mrtg.cfg

[[ ! -d "${MRTGDIR}" ]] && mkdir -p ${MRTGDIR}
[[ ! -d "${WEBDIR}" ]] && mkdir -p ${WEBDIR}

if [ -n "${HOSTS}" ]; then
    hosts=$(echo ${HOSTS} | tr '[,;]' ' ')
    for asset in ${hosts}; do
        COMMUNITY=$(echo $asset | cut -d: -f1)
        HOST=$(echo $asset | cut -d: -f2)
        NAME=$(snmpwalk -Oqv -v2c -c ${COMMUNITY} ${HOST} .1.3.6.1.2.1.1.5)
        [[ ! -f "${MRTGDIR}/conf.d/${NAME}.cfg" ]] && /usr/bin/cfgmaker --ifref=name --output=${MRTGDIR}/conf.d/${NAME}.cfg "${COMMUNITY}@${HOST}"
    done
else
    COMMUNITY=${1:-"public"}
    HOST=${2:-"localhost"}
    NAME=$(snmpwalk -Oqv -v2c -c ${COMMUNITY} ${HOST} .1.3.6.1.2.1.1.5)
    [[ ! -f "${MRTGDIR}/conf.d/${NAME}.cfg" ]] && /usr/bin/cfgmaker --ifref=name --output=${MRTGDIR}/conf.d/${NAME}.cfg "${COMMUNITY}@${HOST}"
fi

env LANG=C /usr/bin/mrtg ${MRTGCFG}
env LANG=C /usr/bin/mrtg ${MRTGCFG}
env LANG=C /usr/bin/mrtg ${MRTGCFG}
/usr/bin/indexmaker --columns=1 ${MRTGCFG} > ${WEBDIR}/index.html
chown -R nginx:nginx ${WEBDIR}

/usr/sbin/nginx &
NGINXID=$!

/usr/sbin/crond -f -L /proc/self/fd/1 -l debug &
CRONDID=$!

trap "kill ${NGINXID} ${CRONDID}" SIGINT SIGHUP SIGTERM SIGQUIT EXIT
wait
