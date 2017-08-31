FROM alpine

LABEL maintainer "Frederico Freire Boaventura <frederico@boaventura.net>"
LABEL version "1.0"

ENV TZ "UTC"
ENV HOSTS "public:localhost"

RUN apk add --update --no-cache tzdata net-snmp-tools mrtg dcron nginx \
    && mkdir -p /etc/mrtg/conf.d

ADD files/mrtg.sh /usr/sbin/mrtg.sh
ADD files/mrtg.cron /etc/crontabs/nginx
ADD files/nginx.conf /etc/nginx/nginx.conf
ADD files/mrtg.cfg /etc/mrtg/mrtg.cfg

CMD ["/usr/sbin/mrtg.sh"]
