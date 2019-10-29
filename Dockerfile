FROM alpine:3.10

ENV TZ "UTC"
ENV HOSTS "public:localhost"

RUN apk add --update --no-cache tzdata net-snmp-tools mrtg dcron nginx \
    && mkdir -p /etc/mrtg/conf.d

ADD files/mrtg.sh /usr/sbin/mrtg.sh
ADD files/mrtg.cron /etc/crontabs/root
ADD files/nginx.conf /etc/nginx/nginx.conf
ADD files/mrtg.cfg /etc/mrtg/mrtg.cfg

CMD ["/usr/sbin/mrtg.sh"]

LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="MRTG" \
      org.label-schema.description="Multi Router Traffic Grapher." \
      org.label-schema.url="https://frederico.cf" \
      org.label-schema.vcs-url=$VCS_URL \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vendor="$VENDOR" \
      org.label-schema.version="$VERSION" \
      org.label-schema.schema-version="1.0" \
      org.label-schema.author="$AUTHOR" \
      org.label-schema.docker.dockerfile="/Dockerfile" \
      org.label-schema.license="MIT"
