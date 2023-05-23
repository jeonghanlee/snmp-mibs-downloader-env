# snmp-mibs-downloader-env

Configuration Environment for the snmp-mibs-downloader at <https://salsa.debian.org/debian/snmp-mibs-downloader>. This repository is designed for specifically the Rocky Linux, because Redhad variant does not have the snmp-mibs-downloader package as a `rpm` format. Please use the Debian package if one wants to use it within Debian variants and one **should not** use this repository on Debian variants.

## Rocky 9

### Setup Commnands


```bash
make init
make install
make setup
make exist
```

