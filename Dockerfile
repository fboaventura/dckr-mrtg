FROM alpine:3

ENV TZ "UTC"
ENV ENABLE_V6 "no"
ENV HOSTS "public:localhost"
ENV USERID "100"
ENV GROUPID "101"
ENV REGENERATEHTML "yes"
ENV INDEXMAKEROPTIONS ""

RUN apk add --update --no-cache \
      bash=~5.2.15-r5 \
      dcron=~4.5-r9 \
      font-space-mono-nerd=~2.3.3-r0 \
      lighttpd=~1.4.73-r0 \
      mrtg=~2.17.10-r1 \
      net-snmp-tools=~5.9.3-r3 \
      perl-cgi=~4.57-r0 \
      perl-rrd=~1.8.0-r2 \
      rrdtool=~1.8.0-r2 \
      rrdtool-cgi=~1.8.0-r2 \
      shadow=~4.13-r4 \
      tzdata=~2023c-r1 \
    && mkdir -p /etc/mrtg/conf.d \
    && mkdir -p /mrtg/cgi-bin /mrtg/html /mrtg/fonts

COPY files/mrtg.sh /usr/sbin/mrtg.sh
COPY files/mrtg.cron /etc/crontabs/root
COPY files/14all.cgi /mrtg/cgi-bin/14all.cgi
COPY files/lighttpd.conf /etc/lighttpd/lighttpd.conf
COPY files/mrtg.cfg /etc/mrtg/mrtg.cfg

CMD ["/usr/sbin/mrtg.sh"]

ARG BUILD_DATE
ARG VCS_REF
ARG VENDOR
ARG VERSION
ARG AUTHOR

LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="MRTG" \
      org.label-schema.description="Multi\ Router\ Traffic\ Grapher." \
      org.label-schema.url="https://fboaventura.dev" \
      org.label-schema.vcs-url="https://github.com/fboaventura/dckr-mrtg" \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vendor="$VENDOR" \
      org.label-schema.version="$VERSION" \
      org.label-schema.schema-version="1.0" \
      org.label-schema.author="$AUTHOR" \
      org.label-schema.docker.dockerfile="/Dockerfile" \
      org.label-schema.license="MIT"
