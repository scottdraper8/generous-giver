#!/usr/bin/env python3
"""Build the FOMOD installer and all eight standalone configuration archives."""

from __future__ import annotations

import json
import re
import stat
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
FOMOD = ROOT / "fomod"
TABLES = Path("METADATA/REALITY/TABLES")
VERSION_PATTERN = re.compile(r"\d+\.\d+(?:\.\d+)?")
XSI_SCHEMA_LOCATION = (
    "{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation"
)


def read_version() -> str:
    root = ET.parse(FOMOD / "info.xml").getroot()
    version = root.findtext("Version")
    if version is None or not VERSION_PATTERN.fullmatch(version):
        raise SystemExit(f"Unsupported or missing FOMOD release version: {version!r}")
    return version


def validate_badge(path: Path, label: str, version: str) -> None:
    root = ET.parse(path).getroot()
    expected_accessible_label = f"{label}: {version}"
    if root.get("aria-label") != expected_accessible_label:
        raise SystemExit(
            f"{path.relative_to(ROOT)} aria-label must be "
            f"{expected_accessible_label!r}."
        )

    titles = [
        element.text
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == "title"
    ]
    if titles != [expected_accessible_label]:
        raise SystemExit(
            f"{path.relative_to(ROOT)} title must be {expected_accessible_label!r}."
        )

    displayed_versions = {
        text
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == "text"
        and (text := (element.text or "").strip())
        and VERSION_PATTERN.fullmatch(text)
    }
    if displayed_versions != {version}:
        raise SystemExit(
            f"{path.relative_to(ROOT)} displays {sorted(displayed_versions)!r}; "
            f"expected only {version!r}."
        )


def validate_release_metadata(version: str) -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    nms_badges = re.findall(
        r"!\[No Man's Sky ([^\]]+)\]\(assets/badges/nms-version\.svg\)",
        readme,
    )
    if nms_badges != [version]:
        raise SystemExit(
            f"README No Man's Sky badge versions are {nms_badges!r}; "
            f"expected exactly {version!r}."
        )
    validate_badge(ROOT / "assets/badges/nms-version.svg", "No Man's Sky", version)

    config = ET.parse(FOMOD / "ModuleConfig.xml").getroot()
    schema_location = config.get(XSI_SCHEMA_LOCATION, "")
    schema_match = re.search(r"ModConfig(\d+\.\d+)\.xsd$", schema_location)
    if schema_match is None:
        raise SystemExit(
            "fomod/ModuleConfig.xml does not declare a supported ModConfig schema."
        )
    fomod_version = schema_match.group(1)
    fomod_badges = re.findall(
        r"!\[FOMOD ([^\]]+)\]\(assets/badges/fomod-version\.svg\)",
        readme,
    )
    if fomod_badges != [fomod_version]:
        raise SystemExit(
            f"README FOMOD badge versions are {fomod_badges!r}; "
            f"expected exactly {fomod_version!r}."
        )
    validate_badge(ROOT / "assets/badges/fomod-version.svg", "FOMOD", fomod_version)


def validate_fomod() -> list[Path]:
    config = ET.parse(FOMOD / "ModuleConfig.xml").getroot()
    for element in config.iter():
        reference = element.get("path") if element.tag == "image" else None
        reference = element.get("source") if element.tag == "folder" else reference
        if reference is None:
            continue
        path = ROOT / reference
        if not path.exists():
            raise SystemExit(f"FOMOD reference does not exist: {reference}")

    payloads = sorted(FOMOD.rglob("*.EXML"))
    if not payloads:
        raise SystemExit("No FOMOD EXML payloads were found.")
    for payload in payloads:
        ET.parse(payload)
    return payloads


def write_zip(path: Path, files: list[tuple[Path, Path]]) -> None:
    with zipfile.ZipFile(
        path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for source, archive_name in sorted(files, key=lambda pair: pair[1].as_posix()):
            if not source.is_file():
                raise SystemExit(f"Archive input is not a file: {source}")
            entry = zipfile.ZipInfo(
                archive_name.as_posix(), date_time=(1980, 1, 1, 0, 0, 0)
            )
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(
                entry,
                source.read_bytes(),
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )

    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise SystemExit(f"Invalid archive generated: {path.name}")


def manual_variant_files(
    quantity: int, dialogue: str, folder_name: str
) -> list[tuple[Path, Path]]:
    source_files = [
        FOMOD / "files" / str(quantity) / TABLES / "COSTTABLE.EXML",
        FOMOD / "files" / str(quantity) / TABLES / "REWARDTABLE.EXML",
        FOMOD
        / "dialogue"
        / str(quantity)
        / dialogue
        / TABLES
        / "NMS_DIALOG_GCALIENPUZZLETABLE.EXML",
    ]
    if any(not path.is_file() for path in source_files):
        missing = next(path for path in source_files if not path.is_file())
        raise SystemExit(f"Missing standalone mod file: {missing.relative_to(ROOT)}")
    return [
        (source, Path(folder_name) / TABLES / source.name) for source in source_files
    ]


def write_release_notes(output: Path, version: str, release_assets: list[str]) -> None:
    base_url = (
        f"https://github.com/scottdraper8/generous-giver/releases/download/v{version}"
    )

    def link(asset: str, label: str) -> str:
        uploaded_name = asset.replace(" ", ".")
        return f"[{label}]({base_url}/{quote(uploaded_name)})"

    lines = [
        "## Recommended: All-in-One Installer",
        "",
        f"{link(release_assets[0], 'Generous Giver - All-in-One Installer')}",
        "",
        "Recommended to use this one! The FOMOD installer lets you choose how many gifts to give "
        "at once and whether to keep the dialogue screen open.",
        "",
        "## Optional manual downloads",
        "",
        "Only use one optional file below if you do not want to use the FOMOD installer. "
        "Extract it into the game's `GAMEDATA/MODS` directory.",
        "",
    ]
    for quantity in (5, 10, 15, 20):
        for dialogue in ("Open", "Closed"):
            asset = f"Generous Giver - {quantity} Gifts - Dialogue {dialogue}.zip"
            behavior = "keeps" if dialogue == "Open" else "closes"
            lines.append(
                f"- {link(asset, asset.removesuffix('.zip'))} — Gives {quantity} gifts and "
                f"{behavior} the dialogue screen after giving."
            )
    lines.append("")
    (output / "release-notes.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: build_release_assets.py OUTPUT_DIRECTORY | --validate-only"
        )

    version = read_version()
    fomod_payloads = validate_fomod()
    validate_release_metadata(version)
    if sys.argv[1] == "--validate-only":
        print(
            f"Validated Generous Giver {version}, FOMOD metadata, badges, and "
            f"{len(fomod_payloads)} EXML payloads."
        )
        return

    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise SystemExit(f"Output directory must be empty: {output}")

    installer_name = f"GenerousGiver-{version}.zip"
    write_zip(
        output / installer_name,
        [
            (path, path.relative_to(ROOT))
            for path in sorted(FOMOD.rglob("*"))
            if path.is_file()
        ],
    )

    nexus_files = [
        {
            "archive": installer_name,
            "display_name": "Generous Giver - All-in-One Installer",
            "category": "main",
            "update_mod_version": True,
        }
    ]
    release_assets = [installer_name]
    for quantity in (5, 10, 15, 20):
        for dialogue in ("open", "closed"):
            dialogue_title = dialogue.title()
            folder_name = f"Generous-Giver-{quantity}-Dialogue-{dialogue_title}"
            archive_name = (
                f"Generous Giver - {quantity} Gifts - Dialogue {dialogue_title}.zip"
            )
            write_zip(
                output / archive_name,
                manual_variant_files(quantity, dialogue, folder_name),
            )
            release_assets.append(archive_name)
            nexus_files.append(
                {
                    "archive": archive_name,
                    "display_name": archive_name.removesuffix(".zip"),
                    "category": "optional",
                    "update_mod_version": False,
                }
            )

    manifest = {
        "version": version,
        "release_assets": release_assets,
        "fomod_payload_count": len(fomod_payloads),
        "nexus_files": nexus_files,
    }
    write_release_notes(output, version, release_assets)
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Built {len(release_assets)} release archives for Generous Giver {version}.")


if __name__ == "__main__":
    main()
