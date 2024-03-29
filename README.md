# snmp-mibs-downloader-env
[![Rocky9](https://github.com/jeonghanlee/snmp-mibs-downloader-env/actions/workflows/rocky9.yml/badge.svg)](https://github.com/jeonghanlee/snmp-mibs-downloader-env/actions/workflows/rocky9.yml)
[![Rocky8](https://github.com/jeonghanlee/snmp-mibs-downloader-env/actions/workflows/rocky8.yml/badge.svg)](https://github.com/jeonghanlee/snmp-mibs-downloader-env/actions/workflows/rocky8.yml)

Configuration Environment for the `snmp-mibs-downloader` at <https://salsa.debian.org/debian/snmp-mibs-downloader>. This repository is designed specifically for the Rocky Linux because the Redhat variant does not have the `snmp-mibs-downloader` package as an `rpm` format. Please use the Debian package if one wants to use it within Debian variants, and one **should not** use this repository on Debian variants.

**Testing in progress**

## Rocky 9

### Setup Commands


```bash
make init
make install
make get
```

### Check 

```
make list
make exist
```

## ``smistrip``
* This repository uses the Debian 11 version `smistrip` file.
* The source and its license are in the repository <https://gitlab.ibr.cs.tu-bs.de/nm/libsmi>. 
