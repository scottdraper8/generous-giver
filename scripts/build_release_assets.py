#!/usr/bin/env python3
"""Build the FOMOD installer and the existing eight standalone archives."""

from __future__ import annotations

import json
import re
import stat
import sys
import xml.etree.ElementTree as ET
import zipfile
from itertools import product
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
FOMOD = ROOT / "fomod"
TABLES = Path("METADATA/REALITY/TABLES")
VERSION_PATTERN = re.compile(r"\d+\.\d+(?:\.\d+)?")
XSI_SCHEMA_LOCATION = (
    "{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation"
)
QUANTITIES = (5, 10, 15, 20)
DIALOGUE_MODES = ("open", "closed")
MULTIPLIER_MODES = ("enabled", "disabled")
AUTOPHAGE_DIALOGUE_MODES = ("keep", "remove")


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


def property_value(parent: ET.Element, name: str) -> str | None:
    child = parent.find(f"./Property[@name='{name}']")
    return None if child is None else child.get("value")


def require_entry(root: ET.Element, container: str, entry_id: str) -> ET.Element:
    entry = root.find(f"./Property[@name='{container}']/Property[@_id='{entry_id}']")
    if entry is None:
        raise SystemExit(f"Missing generated FOMOD entry {entry_id!r}.")
    return entry


def validate_autophage_definitions(quantity: int) -> None:
    cost_path = FOMOD / "files" / str(quantity) / TABLES / "COSTTABLE.EXML"
    cost_root = ET.parse(cost_path).getroot()
    cost_specs = (
        (f"GG_BUI_ATL_C{quantity}", "GcCostSubstance", "ROBOT2", 19 * quantity),
        (f"GG_BUI_SHD_C{quantity}", "GcCostProduct", "DRONE_SHARD", quantity),
        (f"GG_BUI_SCR_C{quantity}", "GcCostItemFromList", None, quantity),
    )
    for entry_id, cost_type, item_id, amount in cost_specs:
        entry = require_entry(cost_root, "InteractionTable", entry_id)
        group = entry.find("./Property[@name='Cost']/Property[@name='GcCostGroup']")
        if group is None:
            raise SystemExit(f"{entry_id} is not a grouped Autophage cost.")
        if property_value(group, "HideOptionIfCantAffordIndex") != "1":
            raise SystemExit(f"{entry_id} does not retain the Autophage state gate.")
        primary = group.find(f".//Property[@name='{cost_type}']")
        if primary is None or property_value(primary, "Amount") != str(amount):
            raise SystemExit(f"{entry_id} does not contain the expected quantity.")
        if item_id is not None and property_value(primary, "Id") != item_id:
            raise SystemExit(f"{entry_id} does not contain the expected gift item.")
        if cost_type == "GcCostItemFromList":
            first_item = primary.find(
                "./Property[@name='ItemList']/Property[@_index='0']"
            )
            indexed_item = primary.find(
                "./Property[@name='ItemList']/Property[@_index='16']"
            )
            if (
                property_value(primary, "Index") != "16"
                or first_item is None
                or indexed_item is None
            ):
                raise SystemExit(
                    f"{entry_id} does not retain the vanilla scrap-item selector."
                )
            if (
                first_item.get("value") != "SALVAGE_TECH6"
                or indexed_item.get("value") != "TRA_TECH1"
            ):
                raise SystemExit(
                    f"{entry_id} changed the vanilla scrap-item candidate list."
                )
        state = group.find(".//Property[@name='GcCostInteractionMissionState']")
        if state is None:
            raise SystemExit(f"{entry_id} is missing the interaction-state cost.")
        required = state.find("./Property[@name='RequiredState']")
        if (
            required is None
            or property_value(required, "InteractionMissionState") != "Unused"
        ):
            raise SystemExit(f"{entry_id} no longer requires an unused interaction.")
        if property_value(state, "TestThisInteraction") != "true":
            raise SystemExit(f"{entry_id} no longer tests the current Autophage.")

    reward_path = FOMOD / "files" / str(quantity) / TABLES / "REWARDTABLE.EXML"
    reward_root = ET.parse(reward_path).getroot()
    standing_entry = require_entry(
        reward_root, "NPCPlanetSiteTable", f"GG_BUI_R_{quantity}"
    )
    standing = standing_entry.find(".//Property[@name='GcRewardFactionStanding']")
    if standing is None:
        raise SystemExit(f"Missing Builders standing reward for quantity {quantity}.")
    faction = standing.find("./Property[@name='Faction']")
    if faction is None or property_value(faction, "MissionFaction") != "Builders":
        raise SystemExit(f"Quantity {quantity} does not reward Builders standing.")
    if {
        property_value(standing, "AmountMin"),
        property_value(standing, "AmountMax"),
    } != {str(quantity)}:
        raise SystemExit(
            f"Quantity {quantity} has an invalid Builders standing reward."
        )

    keep_entry = require_entry(reward_root, "NPCPlanetSiteTable", "GG_BUI_KEEP")
    state_reward = keep_entry.find(
        ".//Property[@name='GcRewardSetInteractionMissionState']"
    )
    if state_reward is None:
        raise SystemExit("GG_BUI_KEEP is not an interaction-state reward.")
    state = state_reward.find("./Property[@name='MissionState']")
    if state is None or property_value(state, "InteractionMissionState") != "Unused":
        raise SystemExit("GG_BUI_KEEP does not retain the Autophage gift option.")
    if property_value(state_reward, "SetForThisInteraction") != "true":
        raise SystemExit("GG_BUI_KEEP does not target the current Autophage.")


def expected_autophage_cost(index: int, quantity: int, multiplier: str) -> str:
    if index % 2 == 0:
        return f"GG_BUI_ATL_C{quantity}" if multiplier == "enabled" else "C_ROBOT2_GIFT"
    if index % 4 == 1:
        return f"GG_BUI_SHD_C{quantity}" if multiplier == "enabled" else "C_SHARD_GIFT"
    return f"GG_BUI_SCR_C{quantity}" if multiplier == "enabled" else "C_SCRAP_GIFT"


def dialogue_payload_path(
    quantity: int,
    dialogue_mode: str,
    multiplier: str,
    autophage_dialogue: str,
) -> Path:
    if (multiplier, autophage_dialogue) == ("enabled", "keep"):
        base = FOMOD / "dialogue" / str(quantity) / dialogue_mode
    else:
        base = (
            FOMOD
            / "autophage-dialogue"
            / multiplier
            / autophage_dialogue
            / str(quantity)
            / dialogue_mode
        )
    return base / TABLES / "NMS_DIALOG_GCALIENPUZZLETABLE.EXML"


def validate_autophage_dialogue(
    quantity: int,
    dialogue_mode: str,
    multiplier: str,
    autophage_dialogue: str,
) -> None:
    path = dialogue_payload_path(
        quantity,
        dialogue_mode,
        multiplier,
        autophage_dialogue,
    )
    root = ET.parse(path).getroot()
    table = root.find("./Property[@name='Table']")
    if table is None:
        raise SystemExit(f"Missing dialogue table in {path.relative_to(ROOT)}.")
    entries = [entry for entry in table if entry.get("_id") == "BUI_NPC"]
    if multiplier == "disabled" and autophage_dialogue == "remove":
        if entries:
            raise SystemExit(
                f"{path.relative_to(ROOT)} should preserve vanilla Autophage data."
            )
        return
    if {entry.get("_index") for entry in entries} != {
        str(index) for index in range(60)
    }:
        raise SystemExit(
            f"{path.relative_to(ROOT)} does not patch all 60 Autophage variants."
        )
    keep = autophage_dialogue == "keep"
    expected_standing = (
        f"GG_BUI_R_{quantity}" if multiplier == "enabled" else "R_BUI_STAND"
    )
    expected_state = "GG_BUI_KEEP" if keep else "R_BUI_GIFT"
    for entry in entries:
        index = int(entry.get("_index", "-1"))
        option = entry.find("./Property[@name='Options']/Property[@_index='1']")
        if option is None:
            raise SystemExit(
                f"Autophage variant {index} is missing its gift option patch."
            )
        expected_cost = expected_autophage_cost(index, quantity, multiplier)
        if property_value(option, "Cost") != expected_cost:
            raise SystemExit(f"Autophage variant {index} has the wrong gift cost.")
        rewards = option.find("./Property[@name='Rewards']")
        reward_values = (
            [] if rewards is None else [item.get("value") for item in rewards]
        )
        if reward_values != [expected_standing, expected_state]:
            raise SystemExit(f"Autophage variant {index} has the wrong rewards.")
        expected_boolean = str(keep).lower()
        if property_value(option, "ReseedInteractionOnUse") != expected_boolean:
            raise SystemExit(
                f"Autophage variant {index} has the wrong reseed behavior."
            )
        if property_value(option, "KeepOpen") != expected_boolean:
            raise SystemExit(
                f"Autophage variant {index} has the wrong dialogue behavior."
            )


def validate_autophage_fomod(config: ET.Element, payloads: list[Path]) -> None:
    steps = config.findall("./installSteps/installStep")
    if [step.get("name") for step in steps] != [
        "Gek, Korvax, and Vy'keen Settings",
        "Autophage Settings",
    ]:
        raise SystemExit(
            "FOMOD must present Autophage settings on an unconditional second page."
        )
    if steps[1].find("visible") is not None:
        raise SystemExit("FOMOD Autophage settings page must always be visible.")
    if [
        group.get("name") for group in steps[0].findall("./optionalFileGroups/group")
    ] != ["Choose an Exact Amount", "Dialogue Behavior"]:
        raise SystemExit("FOMOD first-page section titles are incorrect.")
    if [
        group.get("name") for group in steps[1].findall("./optionalFileGroups/group")
    ] != ["Autophage Gift Multiplier", "Autophage Dialogue Behavior"]:
        raise SystemExit("FOMOD Autophage section titles are incorrect.")
    first_page_options = {
        plugin.get("name")
        for plugin in steps[0].findall("./optionalFileGroups/group/plugins/plugin")
    }
    if not {
        "Keep Dialogue Open",
        "Close dialogue (normal behavior)",
    }.issubset(first_page_options):
        raise SystemExit("FOMOD first-page dialogue option titles are incorrect.")
    normal_dialogue_images = steps[0].findall(
        "./optionalFileGroups/group[@name='Dialogue Behavior']/plugins/plugin/image"
    )
    if normal_dialogue_images:
        raise SystemExit("FOMOD normal dialogue options must not have images.")
    plugins = steps[1].findall("./optionalFileGroups/group/plugins/plugin")
    recommended = {
        plugin.get("name")
        for plugin in plugins
        if plugin.find("./typeDescriptor/type[@name='Recommended']") is not None
    }
    if recommended != {
        "Enable Multiplier",
        "Keep dialogue open and cycle gift option",
    }:
        raise SystemExit(
            "FOMOD Autophage defaults are not the required enabled/keep settings."
        )
    images = {
        plugin.get("name"): image.get("path")
        for plugin in plugins
        if (image := plugin.find("image")) is not None
    }
    expected_images = {
        "Enable Multiplier": "fomod/images/autophage-10.jpg",
        "Disable Multiplier": "fomod/images/autophage-multiplier-disabled.jpg",
    }
    if images != expected_images:
        raise SystemExit("FOMOD Autophage settings have the wrong option images.")

    expected_matrix = set(
        product(
            (str(quantity) for quantity in QUANTITIES),
            DIALOGUE_MODES,
            MULTIPLIER_MODES,
            AUTOPHAGE_DIALOGUE_MODES,
        )
    )
    actual_matrix = set()
    for pattern in config.findall("./conditionalFileInstalls/patterns/pattern"):
        dependencies = {
            dependency.get("flag"): dependency.get("value")
            for dependency in pattern.findall("./dependencies/flagDependency")
        }
        actual_matrix.add(
            (
                dependencies.get("gift_amount"),
                dependencies.get("dialogue_mode"),
                dependencies.get("autophage_multiplier"),
                dependencies.get("autophage_dialogue"),
            )
        )
    if actual_matrix != expected_matrix:
        raise SystemExit(
            "FOMOD conditional installs do not cover every settings permutation."
        )

    if len(payloads) != 40:
        raise SystemExit(
            f"Expected exactly 40 FOMOD EXML payloads; found {len(payloads)}."
        )
    for quantity in QUANTITIES:
        validate_autophage_definitions(quantity)
        for dialogue_mode, multiplier, autophage_dialogue in product(
            DIALOGUE_MODES,
            MULTIPLIER_MODES,
            AUTOPHAGE_DIALOGUE_MODES,
        ):
            validate_autophage_dialogue(
                quantity,
                dialogue_mode,
                multiplier,
                autophage_dialogue,
            )


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
    validate_autophage_fomod(config, payloads)
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
    autophage_dialogue = "keep" if dialogue == "open" else "remove"
    dialogue_source = dialogue_payload_path(
        quantity,
        dialogue,
        "enabled",
        autophage_dialogue,
    )
    source_files = [
        FOMOD / "files" / str(quantity) / TABLES / "COSTTABLE.EXML",
        FOMOD / "files" / str(quantity) / TABLES / "REWARDTABLE.EXML",
        dialogue_source,
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
        "at once, whether to keep the dialogue screen open, and separate multiplier and dialogue "
        "behavior for Autophage.",
        "",
        "## Optional manual downloads",
        "",
        "Only use one optional file below if you do not want to use the FOMOD installer. "
        "Extract it into the game's `GAMEDATA/MODS` directory. Every manual archive enables the "
        "Autophage multiplier. Dialogue Open archives keep and cycle the Autophage gift option; "
        "Dialogue Closed archives close it and remove regifting for that NPC.",
        "",
    ]
    for quantity in (5, 10, 15, 20):
        for dialogue in ("Open", "Closed"):
            asset = f"Generous Giver - {quantity} Gifts - Dialogue {dialogue}.zip"
            behavior = "keeps" if dialogue == "Open" else "closes"
            autophage_behavior = (
                "their gift option stays open and cycles"
                if dialogue == "Open"
                else "their dialogue closes and regifting that NPC is removed"
            )
            lines.append(
                f"- {link(asset, asset.removesuffix('.zip'))} — Gives {quantity} gifts and "
                f"{behavior} Gek, Korvax, and Vy'keen dialogue after giving. The Autophage "
                f"multiplier is enabled; {autophage_behavior}."
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
