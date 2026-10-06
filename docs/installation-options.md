# MIB installation choices

You can generate Management Information Base (MIB) files without installing Net-SNMP, or use them alongside Rocky's Net-SNMP packages. Both choices use the same downloader and produce the same selected official definitions.

## Package roles and requirements

Net-SNMP implements the Simple Network Management Protocol (SNMP).

| Component | Provides | Required when |
| --- | --- | --- |
| This repository's downloader | Official MIB definitions and source records | You need the selected official modules |
| `net-snmp-libs` | Net-SNMP shared libraries and bundled MIBs | Your application uses the packaged Net-SNMP libraries or bundled implementation-specific MIBs |
| `net-snmp-utils` | Commands such as `snmptranslate`, `snmpget`, and `snmpwalk`; pulls in `net-snmp-libs` | You need Rocky's Net-SNMP client commands |
| `net-snmp` | The `snmpd` agent | You need the Net-SNMP `snmpd` agent on this host |

The downloader does not require any of these three Net-SNMP packages. Its Git, Make, Python, GNU Awk, Patch, and Gzip dependencies remain required.

MIB files describe object identifiers, types, and relationships. They do not supply an SNMP library or client, or enable an agent feature. The application that consumes them has its own runtime requirements.

## Independent MIB file generation

The [generation procedure](update-mibs.md) produces the selected official files in `/var/lib/mibs/ietf` and `/var/lib/mibs/iana`. This mode suits an application with its own MIB loader, or a system that prepares MIB files for use elsewhere.

Its checksum and inventory checks work without Net-SNMP. Using the results requires a consuming application and its configured search directories.

## Package MIBs with additional definitions

The [Net-SNMP procedure](use-net-snmp.md) installs `net-snmp-utils`, generates official definitions, and configures the MIB search directories. Installing `net-snmp-utils` supplies `net-snmp-libs` through package dependencies; the agent package is unnecessary for this client workflow.

Package MIBs remain in `/usr/share/snmp/mibs`. Generated definitions remain in `/var/lib/mibs/ietf` and `/var/lib/mibs/iana`. The downloader writes its generated directories rather than replacing package-owned MIB files.

The additional definitions include updated modules that also exist in the package, modules absent from the package, and their selected dependencies. The downloader generates the full selected set rather than only missing files.

The default sources cover the Internet Engineering Task Force (IETF), the Internet Assigned Numbers Authority (IANA), and required IEEE dependencies. They do not include implementation-specific modules such as `NET-SNMP-MIB` and `UCD-SNMP-MIB`; the package supplies those modules.

Net-SNMP searches directories configured through `MIBDIRS` and loads modules requested with `-m`. Later directories take priority when module names overlap. The [Net-SNMP command manual](https://www.net-snmp.org/docs/man/snmpcmd.html) describes both controls.

The Net-SNMP procedure lists the package directory first, then the generated IETF and IANA directories. This order selects generated definitions for duplicate module names while retaining package-specific definitions.
