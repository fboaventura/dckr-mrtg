# fboaventura/dckr-mrtg
[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2Ffboaventura%2Fdckr-mrtg.svg?type=shield)](https://app.fossa.io/projects/git%2Bgithub.com%2Ffboaventura%2Fdckr-mrtg?ref=badge_shield)


Docker instance to run [MRTG](https://oss.oetiker.ch/mrtg/) - The Multi Router Traffic Grapher

## How to use

This instance is published at [Docker Hub](https://hub.docker.com/r/fboaventura/dckr-mrtg/), so it's public available.  All you need to run this instance is:

```bash
$ docker run -d -p 8080:80 -e "HOSTS='public:localhost,community:ipaddress'" fboaventura/dckr-mrtg
```

You can, of course, pass some custom values in order to make it more prone to your usage.  The variables, and their defaults are:

## Environment

```dockerfile
ENV TZ "UTC"
ENV HOSTS "public:localhost"
```

The variable `TZ` is used to setup the timezone to be used by the OS and MRTG to show dates and times.

The variable `HOSTS` is where you may set the hosts to be monitored.  The format to be used is `community:host,community:host,...`

## Persistency

If you plan on keeping this instance running as your MRTG service, you may pass volumes to be used in order to save the information produced by MRTG.  To achieve this:

From the command line:

```bash
$ mkdir html conf.d
$ docker run -d -p 8080:80 -e "HOSTS='public:localhost,community:ipaddress'" -v `pwd`/html:/usr/share/nginx/html -v `pwd`/conf.d:/etc/mrtg/conf.d fboaventura/dckr-mrtg
```

## docker-compose

```yaml
version: "2"
services:
  mrtg:
    image: fboaventura/dckr-mrtg
    hostname: mrtg
    restart: always
    ports:
      - "8880:80"
    volumes:
      - "./conf.d:/etc/mrtg/conf.d"
      - "./html:/usr/share/nginx/html"
    environment:
        TZ: "Brazil/East"
        HOSTS: 'public:192.168.0.123'
    tmpfs:
      - "/run"
```

Once the instance is running, all you have to do is open a web browser and point it to `http://localhost:8080`


## License
[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2Ffboaventura%2Fdckr-mrtg.svg?type=large)](https://app.fossa.io/projects/git%2Bgithub.com%2Ffboaventura%2Fdckr-mrtg?ref=badge_large)