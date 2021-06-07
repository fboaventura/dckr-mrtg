[![GitHub license](https://img.shields.io/github/license/fboaventura/dckr-mrtg)](https://github.com/fboaventura/dckr-mrtg/blob/master/LICENSE)
[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2Ffboaventura%2Fdckr-mrtg.svg?type=shield)](https://app.fossa.io/projects/git%2Bgithub.com%2Ffboaventura%2Fdckr-mrtg?ref=badge_shield)
[![DockerPulls](https://img.shields.io/docker/pulls/fboaventura/dckr-mrtg.svg)](https://hub.docker.com/r/fboaventura/dckr-mrtg)
[![DockerPulls](https://img.shields.io/docker/stars/fboaventura/dckr-mrtg.svg)](https://hub.docker.com/r/fboaventura/dckr-mrtg)
[![GitHub forks](https://img.shields.io/github/forks/fboaventura/dckr-mrtg)](https://github.com/fboaventura/dckr-mrtg/network)
[![GitHub stars](https://img.shields.io/github/stars/fboaventura/dckr-mrtg)](https://github.com/fboaventura/dckr-mrtg/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/fboaventura/dckr-mrtg)](https://github.com/fboaventura/dckr-mrtg/issues)

# fboaventura/dckr-mrtg

Docker instance to run [MRTG] - The Multi Router Traffic Grapher

## Versioning

Until version `2.2.0`, I used [NGINX], and all the HTML files were statically built by [MRTG].  From `2.3.0` onwards, I've implemented the support for [rrdtool](https://oss.oetiker.ch/rrdtool/) and replaced NGINX with [LIGHTTPD], since I needed the support to run CGI scripts.

There is a possible breaking change because I've moved the `WEBDIR` from `/usr/share/nginx/html` to `/mrtg/html`. So please, check all your configuration files if you are getting some path-related error on the graphics.  It's also possible to pass the environment variable `WEBDIR` on the `docker-compose.yml` or command line (`-e`).

I'm fixing the `latest` tag to version `2.2.0` and will move forward with the numbered tagged versions to avoid undesired behavior.

## How to use

This instance is published at [Docker Hub](https://hub.docker.com/r/fboaventura/dckr-mrtg/), and all you need to run is:

```bash
$ docker run -d -p 8080:80 -e "HOSTS='public:localhost:2,community:ipaddress'" fboaventura/dckr-mrtg:v2.3.0
```

You can, of course, pass some custom values to make it more prone to your usage.  The variables and their defaults are:

## Environment

```dockerfile
ENV TZ "UTC"
ENV HOSTS "community:host[:version]"
ENV WEBDIR "/mrtg/html"
```

The variable `TZ` will configure the timezone used by the OS and MRTG to show dates and times.

The variable `HOSTS` is where you may set the hosts that MRTG will monitor.  The format to be used is `community:host[:version],community:host[:version],...`

  Where:

  * **_community_**: is the SNMP community with read access
  * **_host_**: is the IP address or hostname (if Docker can resolve it)
  * **_version_**: can be `1` or `2` for SNMP **1** or **2c**.  If left empty it will assume **2c**.

## Persistency

If you plan on keeping this instance running as your MRTG service, you may pass volumes to be used in order to save the information produced by MRTG.  To achieve this:

From the command line:

```bash
$ mkdir html conf.d
$ docker run -d -p 8080:80 -e "HOSTS='public:localhost,community:ipaddress'" -v `pwd`/html:/mrtg/html -v `pwd`/conf.d:/etc/mrtg/conf.d fboaventura/dckr-mrtg:v2.3.0
```

## docker-compose

```yaml
version: "3.5"

services:
  mrtg:
    image: fboaventura/dckr-mrtg:v2.3.0
    hostname: mrtg
    restart: always
    ports:
      - "8880:80"
    volumes:
      - "./conf.d:/etc/mrtg/conf.d"
      - "./html:/usr/share/nginx/html"
    environment:
        TZ: "Brazil/East"
        HOSTS: "public:192.168.0.123"
        WEBDIR: "/usr/share/nginx/html"
    tmpfs:
      - "/run"
```

Once the instance is running, all you have to do is open a web browser and point it to `http://localhost:8080`

## ChangeLog

### v1.0.0 - 2017.08

- First version

### v1.1 - 2018.10

- 2018.10 - Updated MRTG and Alpine versions

### v1.2 - 2019.05

- Updated Alpine version

### v1.3 - 2019.08

- Updated Alpine version

### v2.1.1 - 2019.10

- Updated Alpine and MRTG Versions

### v2.2.0 - 2020.04

- Updated Alpine version
- Updated `docker-compose.yml` to version `3.5`
- Fixed the fallback for the empty `HOST`

### v2.3.0 - 2021.06

- Updated Alpine version
- Added support for SNMP version
- Added support for `rrdtool`
- Replaced [NGINX] by [LIGHTTPD]
- Changed the HTML folder from `/usr/share/nginx/html` to `/mrtg/html`
- Fixed `latest` tag to `v2.2.0` to prevent compatibility breaking
- Changed the versioning schema to support only tagged versions


## License
[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2Ffboaventura%2Fdckr-mrtg.svg?type=large)](https://app.fossa.io/projects/git%2Bgithub.com%2Ffboaventura%2Fdckr-mrtg?ref=badge_large)



[MRTG]: https://oss.oetiker.ch/mrtg/
[NGINX]: https://nginx.org
[LIGHTTPD]: http://www.lighttpd.net/
