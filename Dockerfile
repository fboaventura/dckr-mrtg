FROM alpine:3.16

ENV TZ "UTC"
ENV ENABLE_V6 "no"
ENV HOSTS "public:localhost"
ENV USERID "100"
ENV GROUPID "101"
ENV REGENERATEHTML "yes"
ENV INDEXMAKEROPTIONS ""

RUN apk add --update --no-cache tzdata net-snmp-tools dcron lighttpd bash \
        mrtg rrdtool rrdtool-cgi perl-rrd perl-cgi font-space-mono-nerd shadow \
    && mkdir -p /etc/mrtg/conf.d \
    && mkdir -p /mrtg/cgi-bin /mrtg/html /mrtg/fonts

ADD files/mrtg.sh /usr/sbin/mrtg.sh
ADD files/mrtg.cron /etc/crontabs/root
ADD files/14all.cgi /mrtg/cgi-bin/14all.cgi
ADD files/lighttpd.conf /etc/lighttpd/lighttpd.conf
ADD files/mrtg.cfg /etc/mrtg/mrtg.cfg

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
