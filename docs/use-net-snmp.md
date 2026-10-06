# Use Net-SNMP with additional MIBs

This procedure combines Rocky's packaged Net-SNMP commands and bundled Management Information Base (MIB) files with the downloader's selected official definitions.

The `net-snmp-utils` package supplies the client commands and requires `net-snmp-libs`. The `net-snmp` agent package is unnecessary unless this host needs `snmpd`. See [MIB installation choices](installation-options.md) for package roles and definition coverage.

## Prerequisites

- Rocky Linux 8.10 or 10.2, with access to the Rocky package repositories and the downloader's official source sites.
- A checkout of this repository, an available `sudo` command, and permission to install system files through it.

## Procedure

1. To provide the Net-SNMP commands and package MIBs, install the client package:

   ```bash
   sudo dnf install -y net-snmp-utils
   ```

   DNF installs the required library dependencies. Package MIBs reside in `/usr/share/snmp/mibs`.

2. To add official definitions, complete [Generate and update official MIBs](update-mibs.md), including its verification.

   The generated modules reside in `/var/lib/mibs/ietf` and `/var/lib/mibs/iana`. Package-owned MIB files retain their contents.

3. In the shell that runs Net-SNMP, set the MIB search directories:

   ```bash
   export MIBDIRS=/usr/share/snmp/mibs:/var/lib/mibs/ietf:/var/lib/mibs/iana
   ```

   Set this variable in each shell or service environment that uses the definitions. The symlinks in `/usr/share/snmp/mibs` do not make Net-SNMP search the generated subdirectories automatically.

   Net-SNMP gives later directories priority for duplicate module names. This order selects generated definitions for overlapping modules and preserves access to package-specific modules.

## Verification

To verify an official module, its IANA dependency, and a package-specific module, translate their object identifiers:

```bash
snmptranslate -m +ENTITY-MIB -On ENTITY-MIB::entPhysicalDescr
snmptranslate -m +IANA-ENTITY-MIB -On IANA-ENTITY-MIB::ianaEntityMIB
snmptranslate -m +NET-SNMP-MIB -On NET-SNMP-MIB::netSnmp
```

The expected output, in command order, is:

```text
.1.3.6.1.2.1.47.1.1.1.1.2
.1.3.6.1.2.1.216
.1.3.6.1.4.1.8072
```

Each command must exit successfully without a missing-module warning. These translations check local definitions; they do not contact a Simple Network Management Protocol (SNMP) agent.

To verify that package-owned MIBs retain their RPM contents, check the package:

```bash
rpm -V net-snmp-libs
```

Successful package verification produces no output.
