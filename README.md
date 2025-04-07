[![GitHub license](https://img.shields.io/github/license/fboaventura/dckr-mrtg)](https://github.com/fboaventura/dckr-mrtg/blob/master/LICENSE)
[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2Ffboaventura%2Fdckr-mrtg.svg?type=shield)](https://app.fossa.io/projects/git%2Bgithub.com%2Ffboaventura%2Fdckr-mrtg?ref=badge_shield)
[![DockerPulls](https://img.shields.io/docker/pulls/fboaventura/dckr-mrtg.svg)](https://hub.docker.com/r/fboaventura/dckr-mrtg)
[![DockerPulls](https://img.shields.io/docker/stars/fboaventura/dckr-mrtg.svg)](https://hub.docker.com/r/fboaventura/dckr-mrtg)
[![GitHub forks](https://img.shields.io/github/forks/fboaventura/dckr-mrtg)](https://github.com/fboaventura/dckr-mrtg/network)
[![GitHub stars](https://img.shields.io/github/stars/fboaventura/dckr-mrtg)](https://github.com/fboaventura/dckr-mrtg/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/fboaventura/dckr-mrtg)](https://github.com/fboaventura/dckr-mrtg/issues)

# fboaventura/dckr-mrtg

Docker instance to run [MRTG] - The Multi Router Traffic Grapher.

This image is built for all the architectures supported by Alpine image. Although not all of them were tested and validated to be working.

| Architecture | Validated? |
|--------------|------------|
| amd64        | Yes        |
| arm64v8      | Yes        |
| arm32v6      | No         |
| arm32v7      | No         |
| i386         | No         |
| ppc64le      | No         |
| s390x        | No         |
| riscv64      | No         |


## Table of Contents

<!--ts-->
- [fboaventura/dckr-mrtg](#fboaventuradckr-mrtg)
  - [Table of Contents](#table-of-contents)
  - [Versioning](#versioning)
  - [MIBs A.K.A. Good to know information](#mibs-aka-good-to-know-information)
  - [How to use](#how-to-use)
    - [Environment](#environment)
    - [Persistence](#persistence)
    - [From the command line:](#from-the-command-line)
    - [docker-compose](#docker-compose)
  - [ChangeLog](#changelog)
    - [v2.5.7 - 2025.04.07](#v257---20250407)
    - [v2.5.6 - 2024.09.20](#v256---20240920)
    - [v2.5.5 - 2024.08.22](#v255---20240822)
    - [v2.5.4 - 2024.07.11](#v254---20240711)
    - [v2.5.3 - 2023.11.25](#v253---20231125)
    - [v2.5.2 - 2023.08.29](#v252---20230829)
    - [v2.5.1 - 2023.01.15](#v251---20230115)
    - [v2.5.0 - 2023.01.15](#v250---20230115)
    - [v2.4.0 - 2022.08.26](#v240---20220826)
    - [v2.3.2 - 2022.08.25](#v232---20220825)
    - [v2.3.1 - 2021.09.03](#v231---20210903)
    - [v2.3.0 - 2021.06](#v230---202106)
    - [v2.2.0 - 2020.04](#v220---202004)
    - [v2.1.1 - 2019.10](#v211---201910)
    - [v1.3 - 2019.08](#v13---201908)
    - [v1.2 - 2019.05](#v12---201905)
    - [v1.1 - 2018.10](#v11---201810)
    - [v1.0.0 - 2017.08](#v100---201708)
  - [License](#license)
<!--te-->

## Versioning

Until version `2.2.0`, I used [NGINX], and all the HTML files were statically built by [MRTG].
From `2.3.0` onwards, I've implemented the support for [rrdtool](https://oss.oetiker.ch/rrdtool/) and
replaced NGINX with [LIGHTTPD], since I needed the support to run CGI scripts.

From version `2.3.0` the `WEBDIR` went from `/usr/share/nginx/html` to `/mrtg/html`.
So please, check all your configuration files if you are getting some path-related error on the graphics.
It's also possible to pass the environment variable `WEBDIR` on the `docker-compose.yml` or command line (`-e`).

Starting on version `2.5.5` the development will be made using branches. The `master` will be the stable version, and the development will be made on the versioned branches.  The auto-build will create images with `-dev` suffix and pure `dev`, instead of `latest`, for the development branches and these images will be deleted as soon as new stable release is made.

## MIBs A.K.A. Good to know information

MRTG uses SNMP to monitor the devices. The SNMP protocol look up for an OID (Object Identifier) in the device and return the value of that OID.

OID is the Object Identifier. It is a unique identifier for a piece of data in the MIB. The OID is a sequence of numbers separated by periods. For example, the OID for the device's name is `.1.3.6.1.2.1.1.5`.

To make life easier, SNMP can use a MIB (Management Information Base) file. The MIB file is a text file that describes the data that can be retrieved from a device. For example, using `SNMPv2-MIB` file we can reach the device's name using `sysName.0` instead of the OID.

Some vendors provide the MIB files for their devices. If you have the MIB file, you can use it to translate the OID to a human-readable name.

This container adds the `net-snmp-libs` packages that contains [these MIB files](http://www.net-snmp.org/docs/mibs/). You can add your custom MIB files to the `/mrtg/mibs` folder. And you may find some useful MIB files at [OIDView](https://www.oidview.com/mibs/detail.html), in the [observium](https://github.com/pgmillon/observium/tree/master/mibs) repository or, in some cases, at the vendor' support site.

## How to use

This instance is published at [Docker Hub], and all
you need to run is:

```bash
$ docker run -d -p 8880:80 -e "HOSTS='public:localhost:2,community:ipaddress'" fboaventura/dckr-mrtg:latest
```

You can, of course, pass some custom values to make it more prone to your usage.  The variables and
their defaults are:

### Environment

```dockerfile
ENV CFGMAKEROPTIONS=""
ENV ENABLE_V6="no"
ENV GRAPHOPTIONS="growright, bits"
ENV GROUPID="101"
ENV HOSTS "community:host[:version[:port]]"
ENV INDEXMAKEROPTIONS=""
ENV MIBSDIR="/mrtg/mibs"
ENV MRTG_COLUMNS=2
ENV PATHPREFIX=""
ENV REGENERATEHTML="yes"
ENV TZ="UTC"
ENV USERID="100"
ENV WEBDIR="/mrtg/html"
```

The variable `CFGMAKEROPTIONS` (default: empty string) allows you to add any extra options passed to `cfgmaker`, e.g. `--zero-speed=1000000000 --show-op-down`. The options can be found in the [manpage](https://oss.oetiker.ch/mrtg/doc/cfgmaker.en.html) for `cfgmaker`.

The variable `ENABLE_V6` (default: "no") will enable IPv6 support in the container.  If you need to monitor IPv6 devices, set this to "yes".

The variable `GRAPHOPTIONS` (default: "growright, bits") will configure the graphs generated by MRTG.  The default is to grow the graph from left to right and show the values in bits.  You can change this to your needs and the available options can be found [here](https://oss.oetiker.ch/mrtg/doc/mrtg-reference.en.html#Options).

The variable `GROUPID` (default: 101) defines the groupid for the lighttpd user.
 Normally this value should be set to the same value as `USERID`, but other values can be used depending on your needs.

The variable `HOSTS` is where you may set the hosts that MRTG will monitor.  The format to be used
is `community:host[:version[:port]],community:host[:version:[port]],...`

  Where:

  * **_community_**: is the SNMP community with read access
  * **_host_**: is the IP address or hostname (if Docker can resolve it)
  * **_version_**: can be `1` or `2` for SNMP **1** or **2c**.  If left empty it will assume **2c**.
  * **_port_**: can be any custom port.  There is one point of attention, if the port is needed, then the version must be set.

The variable `INDEXMAKEROPTIONS` (default: empty string) allows you to add any extra options passed to `indexmaker`, e.g. `--nolegend`. The options can be found in the [manpage](https://oss.oetiker.ch/mrtg/doc/indexmaker.en.html) for `indexmaker`.

The variable `MIBSDIR` (default: "/mrtg/mibs") is the path where the custom MIB files can be stored.  If you have custom MIB files, you can mount a volume to this path to make them available to MRTG. Take into consideration that all files in this directory will be loaded by MRTG.

The variable `MRTG_COLUMNS` (default: 2) defines the number of columns in the index.html file.  This is useful if you have a large number of hosts and want to display them in multiple columns.

The variable `PATHPREFIX` (default: empty string) is the path passed to `indexmaker` to prefix URLs to `rrdviewer` or
any images.
 The format must **NOT** include a trailing slash.  For example, "/mrtg"
 Used with a reverse proxy, this allows mrtg to exist at a subpath rather than the root.

The variable `WEBDIR` (default: "/mrtg/html") is the path where the HTML files are stored.  This is the path where the index.html file is generated and where the RRD files are stored.  If you need to change this path, you can set this variable to the desired path.

The variable `TZ` will configure the timezone used by the OS and MRTG to show dates and times.

The variable `USERID` (default: 100) defines the userid for the lighttpd user. The files in the html directory will be owned by this user.
 Normally this value should be set to 1000 (or above), depending on your needs for mapped volumes.

The variable `REGENERATEHTML` (default: "yes") determines if the index.html file will be regenerated at container restart. The original index.html will be renamed index.old (overwriting any earlier file with that name).
 You should set this value to anything other than "yes" if you have any custom changes to index.html that you do not want overwritten at container restart.

### Persistence

The container will create and use the following directories to store the data and configuration:

* `/etc/mrtg/conf.d`: where the generated and custom configuration files are stored
* `/mrtg/html`: where the HTML and RRD files are stored
* `/mrtg/mibs`: where the custom MIB files can be stored
* `/mrtg/fonts`: where custom fonts can be stored

If you plan on keeping this instance running as your MRTG service, you may pass volumes
to be used to save the information produced by MRTG.  To achieve this:

### From the command line:

```bash
$ mkdir html conf.d
$ docker run -d -p 8880:80 -e "HOSTS='public:localhost,community:ipaddress'" -v `pwd`/html:/mrtg/html -v `pwd`/conf.d:/etc/mrtg/conf.d fboaventura/dckr-mrtg:latest
```

### docker-compose

```yaml
---
services:
  mrtg:
    image: fboaventura/dckr-mrtg:latest
    hostname: mrtg
    restart: always
    ports:
      - "8880:80"
    volumes:
      - "./conf.d:/etc/mrtg/conf.d"
      - "./html:/mrtg/html"
      - "/etc/localtime:/etc/localtime:ro"
      - "/etc/timezone:/etc/timezone:ro"
    environment:
        TZ: "Brazil/East"
        HOSTS: "public:192.168.0.123"
        WEBDIR: "/mrtg/html"
        USERID: 1000
        GROUPID: 1000
        REGENERATEHTML: "yes"
        INDEXMAKEROPTIONS: ""
        CFGMAKEROPTIONS: "--zero-speed=1000000000"
        MRTG_COLUMNS: 2
    tmpfs:
      - "/run"
```

Once the instance is running, all you have to do is open a web browser and point it to `http://localhost:8880` or `http://<server_ip>:8880` and you will see the MRTG index page.

## ChangeLog

### v2.5.7 - 2025.04.07
- Updated packages versions
- Refactored the `mrtg.sh` starting script
- Added support for `supervisord` to manage the processes (Fix #32)
- Added support for [Home Assistant] add-in (Fix #29)

### v2.5.6 - 2024.09.20
- Updated packages versions
- Fixed `indexmaker` and `cfgmaker` options (Fixes #25)
- Added support for [devcontainers](https://containers.dev/)
- Added `provenance` and `SBOM` attestations to the builds

### v2.5.5 - 2024.08.22
- Added versioned `dev` branches for development
- Added the `net-snmp-libs` package to include the MIB files
- Added the `MIBSDIR` environment variable to set the path to the MIB files
- Added a Table of Contents to the `README.md` file
- Added more platforms to the build matrix
- Updated the `14all.cgi` script to match latest Perl coding standards
- Updated the `README.md` file to include information about MIBs and fix typos (Thanks @mlazarov)
- Fixed some of the warnings in the `14all.cgi` script (#21 and #23)
- Fixed the `lighttpd` configuration to remove deprecated options

### v2.5.4 - 2024.07.11
- Updated packages versions
- Updated the `14all.cgi` script, added option to export the data in CSV format
- Added the `MRTG_COLUMNS` environment variable to set the number of columns in the index.html file

### v2.5.3 - 2023.11.25
- Force font cache clean-up to avoid fontconfig errors
- Fix security concerts in Dockerfile
- Fixed errors with lighttpd configuration
- Added fixed versions to packages
- Added command to update alpine packages

### v2.5.2 - 2023.08.29
- Updated Alpine version to reduce vulnerabilities
- Fix missing icon images when using PathPrefix (@michaelkrieger)

### v2.5.1 - 2023.01.15
- Fixed the auto-build to publish multi-arch versions and documentation
- Added volume information to README.md

### v2.5.0 - 2023.01.15
- Added the ability to set `USERID` and `GROUPID` for volume mapping scenarios (@TweakM)
- Added the option to not regenerate the index.html file, applicable when custom/manual changes to this file have been made  (@TweakM)
- Added the ability to specify additional options for `indexmaker` (allowing more customizations)  (@TweakM)
- Updated documentation
- Fixed typo's

### v2.4.0 - 2022.08.26

- Enabled multi-arch building and images at [Docker Hub]
- Released the Docker `latest` tag to follow the releases
- Bumped Alpine version

### v2.3.2 - 2022.08.25

- Added `/etc/localtime` to docker example (@michaelkrieger)
- Added the option to allow use of _Path Prefix_ (@michaelkrieger)
- Updated Alpine version

### v2.3.1 - 2021.09.03

- Fixed README.md example settings for HTML folder (#4)
- Fixed the lighttpd daemon flag
- Added support for a custom port

### v2.3.0 - 2021.06

- Updated Alpine version
- Added support for SNMP version
- Added support for `rrdtool`
- Replaced [NGINX] by [LIGHTTPD]
- Changed the HTML folder from `/usr/share/nginx/html` to `/mrtg/html`
- Fixed `latest` tag to `v2.2.0` to prevent compatibility breaking
- Changed the versioning schema to support only tagged versions

### v2.2.0 - 2020.04

- Updated Alpine version
- Updated `docker-compose.yml` to version `3.5`
- Fixed the fallback for the empty `HOST`

### v2.1.1 - 2019.10

- Updated Alpine and MRTG Versions

### v1.3 - 2019.08

- Updated Alpine version

### v1.2 - 2019.05

- Updated Alpine version

### v1.1 - 2018.10

- 2018.10 - Updated MRTG and Alpine versions

### v1.0.0 - 2017.08

- First version

## License
[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2Ffboaventura%2Fdckr-mrtg.svg?type=large)](https://app.fossa.io/projects/git%2Bgithub.com%2Ffboaventura%2Fdckr-mrtg?ref=badge_large)



[MRTG]: https://oss.oetiker.ch/mrtg/
[NGINX]: https://nginx.org
[LIGHTTPD]: http://www.lighttpd.net/
[Docker Hub]: https://hub.docker.com/r/fboaventura/dckr-mrtg/
[Home Assistant]: https://www.home-assistant.io/
