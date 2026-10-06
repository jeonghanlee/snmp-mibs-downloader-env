# snmp-mibs-downloader-env
[![Rocky9](https://github.com/jeonghanlee/snmp-mibs-downloader-env/actions/workflows/rocky9.yml/badge.svg)](https://github.com/jeonghanlee/snmp-mibs-downloader-env/actions/workflows/rocky9.yml)
[![Rocky8](https://github.com/jeonghanlee/snmp-mibs-downloader-env/actions/workflows/rocky8.yml/badge.svg)](https://github.com/jeonghanlee/snmp-mibs-downloader-env/actions/workflows/rocky8.yml)

This repository installs [Debian's snmp-mibs-downloader](https://salsa.debian.org/debian/snmp-mibs-downloader) and builds official Management Information Base (MIB) definitions on Rocky Linux. The documented procedures target Rocky Linux 8.10 and 10.2. On Debian systems, use the distribution's downloader package.

## Rocky Linux installation choices

MIB generation does not require a Net-SNMP package. Net-SNMP libraries and commands remain separate dependencies of the application that uses the MIBs.

| Purpose | Procedure |
| --- | --- |
| Generate official MIB files for an application or another system | [Generate and update official MIBs](docs/update-mibs.md) |
| Use Rocky's Net-SNMP commands with package MIBs and additional official definitions | [Use Net-SNMP with additional MIBs](docs/use-net-snmp.md) |

See [MIB installation choices](docs/installation-options.md) for package roles, coverage, and search directories. The `net-snmp` agent package is required only when the host needs `snmpd`.

## Official source updates

`make init` selects Debian downloader 1.8 and downloads Request for Comments (RFC) documents and Internet Assigned Numbers Authority (IANA) definitions, with required IEEE dependencies. `make mibs.update` refreshes the source data, and `make mibs.check` verifies its checksums. The [source selection description](docs/mib-sources.md) explains selection rules and source records.

## ``smistrip``
* This repository uses the Debian 11 version `smistrip` file.
* The source and its license are in the repository <https://gitlab.ibr.cs.tu-bs.de/nm/libsmi>. 
