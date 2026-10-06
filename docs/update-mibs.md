# Generate and update official MIBs

This procedure downloads official Management Information Base (MIB) definitions, installs the downloader inputs, and generates MIB files without requiring a Net-SNMP package.

The sources cover the Internet Engineering Task Force (IETF), the Internet Assigned Numbers Authority (IANA), and required IEEE modules. See [MIB source selection](mib-sources.md) for selection rules and source records.

The result contains MIB definitions, not a Simple Network Management Protocol (SNMP) library, client, or agent. For Rocky's Net-SNMP commands, follow [Use Net-SNMP with additional MIBs](use-net-snmp.md), which includes this procedure.

## Prerequisites

- Rocky Linux 8.10 or 10.2, with network access to Debian Salsa, RFC Editor, IANA, and IEEE 802.1.
- A checkout of this repository, an available `sudo` command, and permission to install system files through it.
- A MIB-consuming application or a destination system, if you need to use the definitions after generating them.

## Procedure

Each command must exit successfully before you continue. File checks validate existing definitions and do not replace a successful `get` run.

1. To provide the downloader's dependencies, install the required Rocky packages:

   ```bash
   sudo dnf install -y git make sudo which python3 gawk patch gzip
   ```

   The downloader uses Python 3.6 or later, GNU Awk, Patch, and Gzip. This package list does not install Net-SNMP.

2. To prepare the downloader and fetch the official MIB sources, initialize the checkout:

   ```bash
   make -C <repository_path> init
   ```

   Replace `<repository_path>` with the absolute repository path. The command selects Debian downloader 1.8 and builds the source data in `mibs-src/`.

   For subsequent source updates, use the update command:

   ```bash
   make -C <repository_path> mibs.update
   ```

3. To verify the downloaded files against their recorded SHA-256 values, check the local source data:

   ```bash
   make -C <repository_path> mibs.check
   ```

   The command prints the IETF and IANA module counts, the retrieval time, and `PASS: MIB source checksums`.

4. To install the downloader, module lists, and source archives, install the environment:

   ```bash
   make -C <repository_path> install
   ```

   The installer places the source archives in `/usr/share/snmp/mibs-downloader` and the downloader configuration in `/etc/snmp-mibs-downloader`.

5. To extract the modules from the installed archives, run the downloader:

   ```bash
   make -C <repository_path> get
   ```

   The downloader generates the IETF modules in `/var/lib/mibs/ietf` and the IANA modules in `/var/lib/mibs/iana`.

   These directories contain the full selected module set, including definitions that overlap with package MIBs. Configure the consuming application's search paths separately; this procedure does not install or start an SNMP agent.

## Verification

To verify every generated module against the source data, check the installed modules:

```bash
make -C <repository_path> mibs.installed.check
```

The command must print `PASS: MIB source checksums` and `PASS: <module_count> generated MIB modules`. The count depends on the selected official sources. A missing file or a checksum mismatch fails verification.

To list the modules selected by the installed configuration, inspect the downloader list:

```bash
make -C <repository_path> list
```

The list includes `ENTITY-MIB` and `IANA-ENTITY-MIB`. These checks verify the generated files and inventory without requiring `snmptranslate`. Parsing and runtime use depend on the consuming application.
