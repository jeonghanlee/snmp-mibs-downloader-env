# MIB source selection

The updater builds downloader inputs from official Management Information Base (MIB) definitions. It selects Internet Engineering Task Force (IETF) and Internet Assigned Numbers Authority (IANA) modules, then adds required IEEE modules.

The [generation procedure](update-mibs.md) covers installation and verification on Rocky Linux 8.10 and 10.2 without requiring Net-SNMP. [MIB installation choices](installation-options.md) describes independent generation and use alongside package MIBs.

## Official source selection

The updater reads the [RFC Editor index](https://www.rfc-editor.org/rfc-index.xml), the [IANA MIB registry](https://www.iana.org/assignments/mib-modules), and the [IANA SMI registry](https://www.iana.org/assignments/smi-numbers). The Structure of Management Information (SMI) registry supplies module registrations and RFC references.

RFC candidates include MIB-related titles, the downloader's baseline RFC lists, and IANA SMI references. The updater follows `obsoleted-by` and `updated-by` references and extracts definitions with the repository's `smistrip`.

Additional RFC modules come from documents that are not obsoleted or Historic. Modules from Informational documents require an IANA module registration. The baseline lists' modules remain available, including Simple Network Management Protocol (SNMP) syntax modules.

For duplicate RFC modules, the greatest `LAST-UPDATED` or `REVISION` timestamp takes priority. The greater RFC number breaks a tie. IANA's official file takes priority for an IANA-maintained module.

The updater excludes other ASN.1 definitions without MIB constructs, policy information bases, and named example modules. Additional RFC definitions containing placeholder object identifiers are also excluded.

## Required dependency definitions

The updater includes every MIB file in the IANA MIB registry. It checks that every baseline module remains available and that every referenced IANA module is present.

For an IEEE dependency, the updater selects the greatest published revision in the [IEEE 802.1 MIB module catalog](https://1.ieee802.org/mib-modules/). It downloads that definition and follows its dependencies. The `ieee` source group generates these modules in `/var/lib/mibs/ietf`.

The updater preserves each definition's declared module name. A registry title can differ from that name; the source record retains the title separately.

## Generated data and records

The updater applies Debian's source patches before extraction and the downloader's module corrections afterward. It validates the complete result in a temporary directory before replacing `mibs-src/`.

`mibs-src/` contains the selected source archives, generated downloader lists, metadata, and `sources.json`. The repository's `*-src` rule excludes this generated directory from Git.

`sources.json` records retrieval time, the IANA registry date, source URLs, selected module names, and external imports. It includes SHA-256 values for source files and generated modules. Corrected RFC inputs retain checksums for both the official original and the corrected input.

An update failure preserves the previous source directory and retains the failed temporary directory for inspection. Source updates do not install system files. The `install` target installs the archives and configuration; `get` extracts the modules into `/var/lib/mibs/`.
