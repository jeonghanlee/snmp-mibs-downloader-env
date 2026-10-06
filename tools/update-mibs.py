#!/usr/bin/env python3
"""Build downloader inputs from the official RFC and IANA registries."""

import argparse
import concurrent.futures
import datetime
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from urllib.parse import urlparse, urlunparse
import xml.etree.ElementTree as ET


RFC_BASE = "https://www.rfc-editor.org/rfc"
REGISTRIES = {
    "rfc-index.xml": "https://www.rfc-editor.org/rfc-index.xml",
    "mib-modules.xml": "https://www.iana.org/assignments/mib-modules/mib-modules.xml",
    "smi-numbers.xml": "https://www.iana.org/assignments/smi-numbers/smi-numbers.xml",
    "ieee-mibs.html": "https://1.ieee802.org/mib-modules/",
}
IANA_BASE = "https://www.iana.org/assignments"
RFC_NS = {"r": "https://www.rfc-editor.org/rfc-index"}
IANA_NS = {"i": "http://www.iana.org/assignments"}
MIB_TITLE = re.compile(
    r"\bMIBs?\b|Management Information Base|Managed Objects|"
    r"Textual Conventions|Structure of Management Information", re.I
)
MODULE_NAME = re.compile(r"[A-Za-z][A-Za-z0-9-]*\Z")
MODULE_HEADER = re.compile(r"^\s*([A-Za-z][A-Za-z0-9-]*)\s+DEFINITIONS\b", re.M)
REVISION = re.compile(r'\b(?:LAST-UPDATED|REVISION)\s+"(\d{12}Z)"')
IMPORT = re.compile(r"\bFROM\s+([A-Za-z][A-Za-z0-9-]*)")
SMI_CONSTRUCT = re.compile(r"\b(?:OBJECT-TYPE|MODULE-IDENTITY|TEXTUAL-CONVENTION|TRAP-TYPE)\b")
NETWORK_TIMEOUT = 45
NETWORK_ATTEMPTS = 3
WORKERS = 6
MANIFEST = "sources.json"
GENERATED_MIBS = Path("/var/lib/mibs")
IEEE_HOSTS = {"www.ieee802.org", "ieee802.org", "grouper.ieee.org"}
IEEE_FILENAME = re.compile(r"([A-Za-z][A-Za-z0-9-]*)-(\d{12}Z)\.(?:mib|txt)\Z")
PLACEHOLDER_OID = re.compile(r"::=\s*\{[^}]*\b[xX]{2,}\b[^}]*\}")


class IEEEIndex(HTMLParser):
    def __init__(self):
        super().__init__()
        self.modules = {}

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        url = dict(attrs).get("href", "")
        parsed = urlparse(url)
        match = IEEE_FILENAME.fullmatch(Path(parsed.path).name)
        if not match or parsed.hostname not in IEEE_HOSTS or parsed.scheme not in ("http", "https"):
            return
        name, revision = match.groups()
        url = urlunparse(parsed._replace(scheme="https"))
        previous = self.modules.get(name)
        if previous is None or revision > previous[0]:
            self.modules[name] = (revision, url)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def imports(data):
    text = data.decode("utf-8", errors="replace")
    statement = re.search(r"^\s*IMPORTS\b(.*?);", text, re.M | re.S)
    if statement is None:
        return set()
    return set(IMPORT.findall(re.sub(r"--[^\n]*", "", statement.group(1))))


def fetch(url, destination):
    for attempt in range(NETWORK_ATTEMPTS):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "snmp-mibs-downloader-env"})
            with urllib.request.urlopen(request, timeout=NETWORK_TIMEOUT) as response:
                data = response.read()
            if not data:
                raise ValueError("Empty response: " + url)
            destination.write_bytes(data)
            return {"url": url, "sha256": digest(data)}
        except (OSError, ValueError):
            if attempt + 1 == NETWORK_ATTEMPTS:
                raise
            time.sleep(attempt + 1)


def read_list(path):
    entries = {}
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        source, modules = line.split(None, 1)
        entries[source] = modules.split(":")
    return entries


def extract(smistrip, source, destination, required=()):
    destination.mkdir()
    result = subprocess.run(
        [str(smistrip), "-a", "-d", str(destination), str(source)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
    )
    if result.returncode:
        raise ValueError("smistrip failed for {}: {}".format(source.name, result.stderr))
    modules = {}
    for path in destination.iterdir():
        if not MODULE_NAME.fullmatch(path.name):
            raise ValueError("Invalid module name: " + path.name)
        data = path.read_bytes()
        text = data.decode("utf-8", errors="replace")
        header = MODULE_HEADER.search(text)
        if not header or path.name == "DEFINITIONS":
            continue
        if path.name not in required and not SMI_CONSTRUCT.search(text):
            continue
        if header.group(1) != path.name or not re.search(r"^\s*END\s*$", text, re.M):
            raise ValueError("Incomplete MIB module: {} in {}".format(path.name, source.name))
        modules[path.name] = data
    return modules


def rfc_candidates(index, smi_registry, baseline):
    entries = {}
    selected = set(baseline)
    for entry in index.findall("r:rfc-entry", RFC_NS):
        number = int(entry.findtext("r:doc-id", namespaces=RFC_NS)[3:])
        entries[number] = entry
        if MIB_TITLE.search(entry.findtext("r:title", default="", namespaces=RFC_NS)):
            selected.add(number)
    for xref in smi_registry.findall(".//i:xref[@type='rfc']", IANA_NS):
        reference = xref.get("data", "")
        if re.fullmatch(r"rfc\d+", reference):
            selected.add(int(reference[3:]))
    pending = list(selected)
    while pending:
        entry = entries.get(pending.pop())
        if entry is None:
            continue
        for relation in ("obsoleted-by", "updated-by"):
            for reference in entry.findall("r:{}/r:doc-id".format(relation), RFC_NS):
                if re.fullmatch(r"RFC\d+", reference.text):
                    number = int(reference.text[3:])
                    if number not in selected:
                        selected.add(number)
                        pending.append(number)
    return sorted(selected), entries


def iana_candidates(registry):
    modules = {}
    for entry in registry.findall("i:registry", IANA_NS):
        name = entry.findtext("i:title", namespaces=IANA_NS)
        for file_entry in entry.findall("i:file[@type='mib']", IANA_NS):
            slug = file_entry.text
            if not MODULE_NAME.fullmatch(name) or not re.fullmatch(r"[a-z0-9-]+", slug):
                raise ValueError("Invalid IANA registry entry")
            modules[slug] = name
    if not modules:
        raise ValueError("The IANA registry has no MIB files")
    return modules


def write_list(path, groups):
    rows = ["# Generated from official RFC and IANA sources."]
    for source, names in sorted(groups.items()):
        rows.append("{}\t{}".format(source, ":".join(sorted(names))))
    path.write_text("\n".join(rows) + "\n")


def source_corrections(source, metadata, records):
    corrections = {}
    directory = metadata / "source-patches"
    directory.mkdir()
    for line in (source / "debian/patches/series").read_text().splitlines():
        name = line.strip()
        if not name or name.startswith("#"):
            continue
        if Path(name).name != name:
            raise ValueError("Invalid source patch name: " + name)
        original = source / "debian/patches" / name
        data = original.read_bytes()
        targets = re.findall(r"^\+\+\+ b/mibrfcs/rfc(\d+)\.txt\s*$", data.decode(), re.M)
        if len(targets) != 1:
            raise ValueError("Expected one RFC target in source patch: " + name)
        copied = directory / name
        copied.write_bytes(data)
        records["metadata/source-patches/" + name] = {"sha256": digest(data)}
        corrections.setdefault(int(targets[0]), []).append(copied)
    return corrections


def build(args, stage):
    source = args.source.resolve()
    baseline_rfc = read_list(source / "rfclist")
    baseline_ianarfc = read_list(source / "ianarfclist")
    baseline_iana = read_list(source / "ianalist")
    baseline_names = {name for entries in (baseline_rfc, baseline_ianarfc, baseline_iana)
                      for names in entries.values() for name in names}
    metadata = stage / "metadata"
    metadata.mkdir()
    registries = {}
    for filename, url in REGISTRIES.items():
        registries["metadata/" + filename] = fetch(url, metadata / filename)
    index = ET.parse(str(metadata / "rfc-index.xml")).getroot()
    smi_registry = ET.parse(str(metadata / "smi-numbers.xml")).getroot()
    iana_registry = ET.parse(str(metadata / "mib-modules.xml")).getroot()
    corrections = source_corrections(source, metadata, registries)
    baseline_numbers = {int(number) for number in set(baseline_rfc) | set(baseline_ianarfc)}
    rfcs, rfc_entries = rfc_candidates(index, smi_registry, baseline_numbers)
    registered_names = {entry.text for entry in smi_registry.findall(".//i:description", IANA_NS)
                        if MODULE_NAME.fullmatch(entry.text or "")}
    iana = iana_candidates(iana_registry)
    work = stage / "work"
    work.mkdir()
    (work / "mibrfcs").mkdir()
    (stage / "mibrfcs").mkdir()
    (stage / "mibiana").mkdir()
    (stage / "mibieee").mkdir()
    chosen = {}
    fetched = {}
    total = len(rfcs) + len(iana)
    print("Fetching {} RFC candidates and {} IANA MIB files".format(len(rfcs), len(iana)), flush=True)

    def process_rfc(number):
        filename = "rfc{}.txt".format(number)
        path = work / "mibrfcs" / filename
        record = fetch(RFC_BASE + "/" + filename, path)
        for correction in corrections.get(number, []):
            result = subprocess.run(
                ["patch", "--batch", "-p1", "-d", str(work), "-i", str(correction)],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
            )
            if result.returncode:
                raise ValueError("Source correction failed for {}:\n{}".format(filename, result.stdout))
        if number in corrections:
            record["upstream_sha256"] = record["sha256"]
            record["sha256"] = digest(path.read_bytes())
            record["corrections"] = ["metadata/source-patches/" + p.name for p in corrections[number]]
        modules = extract(args.smistrip.resolve(), path, work / str(number), baseline_names)
        return number, record, modules

    def process_iana(slug):
        path = stage / "mibiana" / slug
        record = fetch("{0}/{1}/{1}".format(IANA_BASE, slug), path)
        modules = extract(args.smistrip.resolve(), path, work / slug)
        if len(modules) != 1:
            raise ValueError("Expected one complete IANA module: " + slug)
        record["registry_title"] = iana[slug]
        return slug, record, modules

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(process_rfc, number) for number in rfcs]
        futures.extend(executor.submit(process_iana, slug) for slug in iana)
        for count, future in enumerate(concurrent.futures.as_completed(futures), 1):
            origin, record, modules = future.result()
            fetched[origin] = record
            for name, data in modules.items():
                if re.search(r"EXAMPLE|^MY-", name):
                    continue
                if isinstance(origin, int) and name not in baseline_names:
                    entry = rfc_entries.get(origin)
                    if entry is None or entry.find("r:obsoleted-by", RFC_NS) is not None:
                        continue
                    status = entry.findtext("r:current-status", namespaces=RFC_NS)
                    if status == "HISTORIC" or (status == "INFORMATIONAL" and name not in registered_names):
                        continue
                    if PLACEHOLDER_OID.search(data.decode("utf-8", errors="replace")):
                        continue
                revisions = REVISION.findall(data.decode("utf-8", errors="replace"))
                rank = (max(revisions, default=""), origin if isinstance(origin, int) else 0)
                candidate = {"origin": origin, "data": data, "rank": rank}
                previous = chosen.get(name)
                if isinstance(origin, str) or previous is None:
                    chosen[name] = candidate
                elif isinstance(previous["origin"], int) and rank > previous["rank"]:
                    chosen[name] = candidate
            if count % 50 == 0 or count == total:
                print("Processed {}/{} sources".format(count, total), flush=True)
    ieee = IEEEIndex()
    ieee.feed((metadata / "ieee-mibs.html").read_text())
    while True:
        dependencies = {name for candidate in chosen.values()
                        for name in imports(candidate["data"])
                        if name not in chosen}
        pending = sorted(dependencies & set(ieee.modules))
        if not pending:
            break
        for name in pending:
            url = ieee.modules[name][1]
            filename = Path(urlparse(url).path).name
            path = stage / "mibieee" / filename
            record = fetch(url, path)
            modules = extract(args.smistrip.resolve(), path, work / filename)
            if name not in modules:
                raise ValueError("Missing module in IEEE source: " + name)
            origin = "ieee/" + filename
            fetched[origin] = record
            for module, data in modules.items():
                chosen[module] = {"origin": origin, "data": data, "rank": ("", 0)}
            print("Included IEEE dependency: " + name, flush=True)
    missing = baseline_names - set(chosen)
    if missing:
        raise ValueError("Existing modules are missing: " + ", ".join(sorted(missing)))

    fallback_iana = {name for names in baseline_ianarfc.values() for name in names}
    lists = {"rfclist": {}, "ianarfclist": {}, "ianalist": {}, "ieeelist": {}}
    inventory = {}
    validation = stage / "validation"
    validation.mkdir()
    used = set()
    for name, candidate in sorted(chosen.items()):
        origin = candidate["origin"]
        if isinstance(origin, str) and origin.startswith("ieee/"):
            list_name, group, filename = "ieeelist", "ietf", "mibieee/" + origin[5:]
            list_source = origin[5:]
        elif isinstance(origin, str):
            list_name, group, filename = "ianalist", "iana", "mibiana/" + origin
            list_source = origin
        else:
            group = "iana" if name in fallback_iana or name.startswith("IANA") else "ietf"
            list_name = "ianarfclist" if group == "iana" else "rfclist"
            filename = "mibrfcs/rfc{}.txt".format(origin)
            list_source = str(origin)
        lists[list_name].setdefault(list_source, []).append(name)
        inventory[name] = {"group": group, "source": filename}
        used.add(origin)
        (validation / name).write_bytes(candidate["data"])
    sources = dict(registries)
    for origin in sorted(used, key=str):
        if isinstance(origin, int):
            filename = "mibrfcs/rfc{}.txt".format(origin)
            shutil.copyfile(str(work / filename), str(stage / filename))
        elif origin.startswith("ieee/"):
            filename = "mibieee/" + origin[5:]
        else:
            filename = "mibiana/" + origin
        sources[filename] = fetched[origin]
    for filename, entries in lists.items():
        write_list(stage / filename, entries)
        sources[filename] = {"sha256": digest((stage / filename).read_bytes())}
    patch = subprocess.run(
        ["patch", "--batch", "-d", str(validation), "-i", str(source / "rfcmibs.diff")],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
    )
    if patch.returncode:
        raise ValueError("RFC corrections failed:\n" + patch.stdout)
    for name, record in inventory.items():
        record["sha256"] = digest((validation / name).read_bytes())
    unresolved = sorted({dependency for path in validation.iterdir() if path.is_file()
                         for dependency in imports(path.read_bytes())
                         if dependency not in inventory})
    missing_iana = [name for name in unresolved if name.startswith("IANA")]
    if missing_iana:
        raise ValueError("Missing IANA dependencies: " + ", ".join(missing_iana))
    manifest = {
        "schema": 1,
        "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "iana_registry_updated": iana_registry.findtext("i:updated", namespaces=IANA_NS),
        "rfc_candidates": rfcs,
        "files": sources,
        "modules": inventory,
        "external_imports": unresolved,
    }
    (stage / MANIFEST).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    shutil.rmtree(str(work))
    shutil.rmtree(str(validation))
    return manifest


def check(output):
    manifest = json.loads((output / MANIFEST).read_text())
    if manifest.get("schema") != 1 or not manifest.get("modules"):
        raise ValueError("Invalid MIB source manifest")
    for filename, record in manifest["files"].items():
        path = Path(filename)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Invalid source path: " + filename)
        if digest((output / path).read_bytes()) != record["sha256"]:
            raise ValueError("Source checksum mismatch: " + filename)
    for group in ("ietf", "iana"):
        count = sum(record["group"] == group for record in manifest["modules"].values())
        print("{} modules: {}".format(group.upper(), count))
    print("Sources retrieved: " + manifest["retrieved_at"])
    print("PASS: MIB source checksums")
    return manifest


def check_installed(output):
    manifest = check(output)
    for name, record in sorted(manifest["modules"].items()):
        if not MODULE_NAME.fullmatch(name) or record["group"] not in ("ietf", "iana"):
            raise ValueError("Invalid generated module entry: " + name)
        path = GENERATED_MIBS / record["group"] / name
        if digest(path.read_bytes()) != record["sha256"]:
            raise ValueError("Generated module checksum mismatch: " + str(path))
    print("PASS: {} generated MIB modules".format(len(manifest["modules"])))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("update", "check", "installed"))
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--smistrip", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=WORKERS)
    args = parser.parse_args()
    if not 1 <= args.workers <= WORKERS:
        parser.error("--workers must be between 1 and {}".format(WORKERS))
    output = args.output.absolute()
    if args.action == "check":
        check(output)
        return
    if args.action == "installed":
        check_installed(output)
        return
    stage = Path(tempfile.mkdtemp(prefix="mibs-stage-", suffix="-src", dir=str(output.parent)))
    try:
        build(args, stage)
        check(stage)
        backup = stage.with_name(stage.name.replace("mibs-stage-", "mibs-backup-"))
        if output.exists():
            output.rename(backup)
        try:
            stage.rename(output)
        except OSError:
            if backup.exists():
                backup.rename(output)
            raise
        if backup.exists():
            shutil.rmtree(str(backup))
        print("PASS: MIB sources updated in " + str(output))
    except Exception:
        print("Retained update workspace: " + str(stage), file=sys.stderr)
        raise


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, ET.ParseError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        sys.exit(1)
