FROM alpine:3

ENV CFGMAKEROPTIONS=""
ENV ENABLE_V6="no"
ENV GRAPHOPTIONS="growright, bits"
ENV GROUPID="101"
ENV HOSTS="public:localhost"
ENV INDEXMAKEROPTIONS=""
ENV MIBSDIR="/mrtg/mibs"
ENV MRTG_COLUMNS=2
ENV PATHPREFIX=""
ENV REGENERATEHTML="yes"
ENV TZ="UTC"
ENV USERID="100"
ENV WEBDIR="/mrtg/html"

RUN apk add --update --no-cache \
    bash=~5.2.37-r0 \
    dcron=~4.6-r0 \
    font-space-mono-nerd=~3.2.1-r0 \
    libsmi=~0.5.0-r4 \
    lighttpd=~1.4.79-r0 \
    mrtg=~2.17.10-r1 \
    net-snmp-libs=~5.9.4-r1 \
    net-snmp-tools=~5.9.4-r1 \
    perl-cgi=~4.68-r0 \
    perl-dev=~5.40.3-r0 \
    perl-rrd=~1.9.0-r4 \
    rrdtool-cgi=~1.9.0-r4 \
    rrdtool=~1.9.0-r4 \
    shadow=~4.17.3-r0 \
    supervisor=~4.2.5-r5 \
    supervisor-pyc=~4.2.5-r5 \
    tzdata=~2025b-r0 \
    && apk upgrade --no-cache \
    && rm -rf /var/cache/apk/* \
    && mkdir -p /etc/supervisor.d /var/log/supervisor/ \
    && mkdir -p /etc/mrtg/conf.d \
    && mkdir -p /mrtg/cgi-bin /mrtg/html /mrtg/fonts /mrtg/mibs

COPY files/mrtg.sh /usr/sbin/mrtg.sh
COPY files/mrtg.cron /etc/crontabs/root
COPY files/14all.cgi /mrtg/cgi-bin/14all.cgi
COPY files/lighttpd.conf /etc/lighttpd/lighttpd.conf
COPY files/mrtg.cfg /etc/mrtg/mrtg.cfg
COPY files/opensans.ttf /mrtg/fonts/opensans.ttf
COPY files/icons /mrtg/icons
COPY files/sv-_base.ini /etc/supervisor.d/000-base.ini
COPY files/sv-crond.ini /etc/supervisor.d/crond.ini
COPY files/sv-lighttpd.ini /etc/supervisor.d/lighttpd.ini

CMD ["/usr/sbin/mrtg.sh"]

ARG BUILD_DATE
ARG VCS_REF
ARG VENDOR
ARG VERSION
ARG AUTHOR

LABEL \
    org.opencontainers.image.authors="Frederico Freire Boaventura" \
    org.opencontainers.image.created=$BUILD_DATE \
    org.opencontainers.image.description="Docker instance to run MRTG - The Multi Router Traffic Grapher" \
    org.opencontainers.image.documentation="https://github.com/fboaventura/dckr-mrtg/README.md" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.revision=$VCS_REF \
    org.opencontainers.image.source="https://github.com/fboaventura/dckr-mrtg" \
    org.opencontainers.image.title="fboaventura/dckr-mrtg" \
    org.opencontainers.image.url="https://fboaventura.dev" \
    org.opencontainers.image.vendor="Frederico Freire Boaventura" \
    org.opencontainers.image.version="$VERSION"
