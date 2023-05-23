# snmp-mibs-downloader-env
[![Rocky9](https://github.com/jeonghanlee/snmp-mibs-downloader-env/actions/workflows/rocky9.yml/badge.svg)](https://github.com/jeonghanlee/snmp-mibs-downloader-env/actions/workflows/rocky9.yml)
[![Rocky8](https://github.com/jeonghanlee/snmp-mibs-downloader-env/actions/workflows/rocky8.yml/badge.svg)](https://github.com/jeonghanlee/snmp-mibs-downloader-env/actions/workflows/rocky8.yml)

Configuration Environment for the snmp-mibs-downloader at <https://salsa.debian.org/debian/snmp-mibs-downloader>. This repository is designed for specifically the Rocky Linux, because Redhad variant does not have the snmp-mibs-downloader package as a `rpm` format. Please use the Debian package if one wants to use it within Debian variants and one **should not** use this repository on Debian variants.

## Rocky 9

### Setup Commnands


```bash
make init
make install
make setup
make exist
```

