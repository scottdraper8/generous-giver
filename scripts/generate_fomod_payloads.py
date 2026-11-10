#!/usr/bin/env python3
"""Generate the quantity-specific Autophage FOMOD payload matrix."""

from __future__ import annotations

import copy
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
FOMOD = ROOT / "fomod"
TABLES = Path("METADATA/REALITY/TABLES")
QUANTITIES = (5, 10, 15, 20)
DIALOGUE_MODES = ("open", "closed")
MULTIPLIER_MODES = ("enabled", "disabled")
AUTOPHAGE_DIALOGUE_MODES = ("keep", "remove")
DEFAULT_AUTOPHAGE_SETTINGS = ("enabled", "keep")
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"

ET.register_namespace("xsi", XSI_NAMESPACE)


def property_element(
    name: str,
    value: str | None = None,
    *,
    entry_id: str | None = None,
    index: int | None = None,
) -> ET.Element:
    attributes = {"name": name}
    if value is not None:
        attributes["value"] = value
    if entry_id is not None:
        attributes["_id"] = entry_id
    if index is not None:
        attributes["_index"] = str(index)
    return ET.Element("Property", attributes)


def add_property(
    parent: ET.Element,
    name: str,
    value: str | None = None,
    *,
    entry_id: str | None = None,
    index: int | None = None,
) -> ET.Element:
    child = property_element(
        name,
        value,
        entry_id=entry_id,
        index=index,
    )
    parent.append(child)
    return child


def serialize(root: ET.Element) -> bytes:
    ET.indent(root, space="  ")
    body = cast(bytes, ET.tostring(root, encoding="utf-8"))
    return b"<?xml version='1.0' encoding='utf-8'?>\n" + body + b"\n"


def write_xml(path: Path, root: ET.Element) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(serialize(root))


def require_child(parent: ET.Element, name: str) -> ET.Element:
    child = parent.find(f"./Property[@name='{name}']")
    if child is None:
        raise SystemExit(f"Missing Property {name!r} in generated payload input.")
    return child


def ensure_child(parent: ET.Element, name: str) -> ET.Element:
    child = parent.find(f"./Property[@name='{name}']")
    if child is None:
        child = add_property(parent, name)
    return child


def remove_generated_entries(container: ET.Element) -> None:
    for entry in list(container):
        if entry.get("_id", "").startswith("GG_BUI_"):
            container.remove(entry)


def add_cost_entry_fields(entry: ET.Element, entry_id: str) -> None:
    add_property(entry, "Id", entry_id)
    add_property(entry, "DisplayCost", "true")
    add_property(entry, "DontCharge", "false")
    add_property(entry, "HideOptionAndDisplayCostOnly", "false")
    add_property(entry, "DisplayOnlyCostIfCantAfford", "false")
    add_property(entry, "HideCostStringIfCanAfford", "false")
    add_property(entry, "RemoveOptionIfCantAfford", "false")
    add_property(entry, "InvertCanAffordOutcome", "false")
    add_property(entry, "MustAffordInCreative", "false")
    add_property(entry, "CommunityContributionValue", "0")
    add_property(entry, "CommunityContributionCapLocID", "UI_COMMUNITY_CAP_REACHED")
    add_property(entry, "CannotAffordOSDMsg", "")
    add_property(entry, "MissionMessageWhenCharged", "")


def interaction_state_cost() -> ET.Element:
    wrapper = property_element("Costs", "GcCostInteractionMissionState")
    state = add_property(wrapper, "GcCostInteractionMissionState")
    required = add_property(state, "RequiredState", "GcInteractionMissionState")
    add_property(required, "InteractionMissionState", "Unused")
    add_property(state, "CantAffordLocID", "")
    add_property(state, "CanAffordLocID", "")
    add_property(state, "AlsoAcceptMaintenanceDone", "false")
    add_property(state, "TestThisInteraction", "true")
    interaction = add_property(
        state,
        "ThisInteractionClassInMyBuilding",
        "GcInteractionType",
    )
    add_property(interaction, "InteractionType", "None")
    return wrapper


def substance_cost(amount: int) -> ET.Element:
    wrapper = property_element("Costs", "GcCostSubstance")
    substance = add_property(wrapper, "GcCostSubstance")
    default = add_property(substance, "Default", "GcDefaultMissionSubstanceEnum")
    add_property(default, "DefaultSubstanceType", "None")
    add_property(substance, "Id", "ROBOT2")
    add_property(substance, "UseScanEventToDetermineLocalSubstance", "")
    add_property(substance, "UseSpecificPlanetIndexForLocalSubstance", "-1")
    add_property(substance, "UseRandomPlanetIndex", "false")
    local_type = add_property(substance, "LocalSubstanceType", "GcLocalSubstanceType")
    add_property(local_type, "LocalSubstanceType", "AnyDeposit")
    add_property(substance, "Amount", str(amount))
    add_property(substance, "UseDefaultAmount", "false")
    add_property(substance, "TakeAmountFromSeasonData", "false")
    return wrapper


def product_cost(amount: int) -> ET.Element:
    wrapper = property_element("Costs", "GcCostProduct")
    product = add_property(wrapper, "GcCostProduct")
    default = add_property(product, "Default", "GcDefaultMissionProductEnum")
    add_property(default, "DefaultProductType", "None")
    add_property(product, "Id", "DRONE_SHARD")
    add_property(product, "Amount", str(amount))
    add_property(product, "UseDefaultAmount", "false")
    add_property(product, "TakeIDFromSeasonData", "false")
    return wrapper


def scrap_cost(amount: int) -> ET.Element:
    wrapper = property_element("Costs", "GcCostItemFromList")
    item_cost = add_property(wrapper, "GcCostItemFromList")
    add_property(item_cost, "Amount", str(amount))
    item_list = add_property(item_cost, "ItemList")
    items = (
        "SALVAGE_TECH6",
        "TRA_ALLOY1",
        "TRA_ALLOY2",
        "TRA_ALLOY3",
        "TRA_ALLOY4",
        "TRA_ALLOY5",
        "TRA_COMPONENT1",
        "TRA_COMPONENT2",
        "TRA_COMPONENT3",
        "TRA_COMPONENT4",
        "TRA_COMPONENT5",
        "TRA_ENERGY1",
        "TRA_ENERGY2",
        "TRA_ENERGY3",
        "TRA_ENERGY4",
        "TRA_ENERGY5",
        "TRA_TECH1",
        "TRA_TECH2",
        "TRA_TECH3",
        "TRA_TECH4",
        "TRA_TECH5",
    )
    for index, item in enumerate(items):
        add_property(item_list, "ItemList", item, index=index)
    add_property(item_cost, "Index", "16")
    add_property(item_cost, "CostStringCantAfford", "")
    return wrapper


def cost_entry(entry_id: str, primary_cost: ET.Element) -> ET.Element:
    entry = property_element(
        "InteractionTable",
        "GcCostTableEntry",
        entry_id=entry_id,
    )
    add_cost_entry_fields(entry, entry_id)
    cost = add_property(entry, "Cost", "GcCostGroup")
    group = add_property(cost, "GcCostGroup")
    add_property(group, "Text", "")
    add_property(group, "TakeTextFromIndex", "0")
    add_property(group, "HideOptionIfCantAffordIndex", "1")
    test = add_property(group, "Test", "GcMissionConditionTest")
    add_property(test, "ConditionTest", "AllTrue")
    costs = add_property(group, "Costs")
    costs.append(primary_cost)
    costs.append(interaction_state_cost())
    return entry


def reward_entry(entry_id: str, reward: ET.Element) -> ET.Element:
    entry = property_element(
        "NPCPlanetSiteTable",
        "GcGenericRewardTableEntry",
        entry_id=entry_id,
    )
    add_property(entry, "Id", entry_id)
    reward_list = add_property(entry, "List", "GcRewardTableItemList")
    add_property(reward_list, "RewardChoice", "GiveAll")
    add_property(reward_list, "OverrideZeroSeed", "false")
    add_property(reward_list, "UseInventoryChoiceOverride", "false")
    add_property(reward_list, "IncrementStat", "")
    items = add_property(reward_list, "List")
    item = add_property(items, "List", "GcRewardTableItem", index=0)
    add_property(item, "PercentageChance", "100.000000")
    add_property(item, "LabelID", "")
    item.append(reward)
    return entry


def standing_reward(quantity: int) -> ET.Element:
    wrapper = property_element("Reward", "GcRewardFactionStanding")
    standing = add_property(wrapper, "GcRewardFactionStanding")
    faction = add_property(standing, "Faction", "GcMissionFaction")
    add_property(faction, "MissionFaction", "Builders")
    add_property(standing, "AmountMin", str(quantity))
    add_property(standing, "AmountMax", str(quantity))
    add_property(standing, "SetToMinBeforeAdd", "false")
    add_property(standing, "TryToUseMissionBoardOriginUA", "false")
    return wrapper


def keep_available_reward() -> ET.Element:
    wrapper = property_element("Reward", "GcRewardSetInteractionMissionState")
    state_reward = add_property(wrapper, "GcRewardSetInteractionMissionState")
    state = add_property(state_reward, "MissionState", "GcInteractionMissionState")
    add_property(state, "InteractionMissionState", "Unused")
    add_property(state_reward, "SetForThisInteraction", "true")
    interaction = add_property(
        state_reward,
        "SetForInteractionClassInMyBuilding",
        "GcInteractionType",
    )
    add_property(interaction, "InteractionType", "None")
    return wrapper


def update_quantity_tables(quantity: int) -> None:
    cost_path = FOMOD / "files" / str(quantity) / TABLES / "COSTTABLE.EXML"
    cost_root = ET.parse(cost_path).getroot()
    costs = ensure_child(cost_root, "InteractionTable")
    remove_generated_entries(costs)
    costs.extend(
        (
            cost_entry(f"GG_BUI_ATL_C{quantity}", substance_cost(19 * quantity)),
            cost_entry(f"GG_BUI_SHD_C{quantity}", product_cost(quantity)),
            cost_entry(f"GG_BUI_SCR_C{quantity}", scrap_cost(quantity)),
        )
    )
    write_xml(cost_path, cost_root)

    reward_path = FOMOD / "files" / str(quantity) / TABLES / "REWARDTABLE.EXML"
    reward_root = ET.parse(reward_path).getroot()
    rewards = ensure_child(reward_root, "NPCPlanetSiteTable")
    remove_generated_entries(rewards)
    rewards.extend(
        (
            reward_entry(f"GG_BUI_R_{quantity}", standing_reward(quantity)),
            reward_entry("GG_BUI_KEEP", keep_available_reward()),
        )
    )
    write_xml(reward_path, reward_root)


def gift_cost(index: int, quantity: int, multiplier: str) -> str:
    if index % 2 == 0:
        return f"GG_BUI_ATL_C{quantity}" if multiplier == "enabled" else "C_ROBOT2_GIFT"
    if index % 4 == 1:
        return f"GG_BUI_SHD_C{quantity}" if multiplier == "enabled" else "C_SHARD_GIFT"
    return f"GG_BUI_SCR_C{quantity}" if multiplier == "enabled" else "C_SCRAP_GIFT"


def autophage_entry(
    index: int,
    quantity: int,
    multiplier: str,
    dialogue_behavior: str,
) -> ET.Element:
    entry = property_element(
        "Table",
        "GcAlienPuzzleEntry",
        entry_id="BUI_NPC",
        index=index,
    )
    options = add_property(entry, "Options")
    option = add_property(options, "Options", "GcAlienPuzzleOption", index=1)
    add_property(option, "Cost", gift_cost(index, quantity, multiplier))
    rewards = add_property(option, "Rewards")
    standing = f"GG_BUI_R_{quantity}" if multiplier == "enabled" else "R_BUI_STAND"
    add_property(rewards, "Rewards", standing, index=0)
    state_reward = "GG_BUI_KEEP" if dialogue_behavior == "keep" else "R_BUI_GIFT"
    add_property(rewards, "Rewards", state_reward, index=1)
    keep = dialogue_behavior == "keep"
    add_property(option, "ReseedInteractionOnUse", str(keep).lower())
    add_property(option, "KeepOpen", str(keep).lower())
    return entry


def replace_autophage_entries(
    root: ET.Element,
    quantity: int,
    multiplier: str,
    dialogue_behavior: str,
) -> None:
    table = require_child(root, "Table")
    for entry in list(table):
        if entry.get("_id") == "BUI_NPC":
            table.remove(entry)
    if multiplier == "disabled" and dialogue_behavior == "remove":
        return
    for index in range(60):
        table.append(autophage_entry(index, quantity, multiplier, dialogue_behavior))


def update_dialogue_payloads(quantity: int, dialogue_mode: str) -> None:
    default_path = (
        FOMOD
        / "dialogue"
        / str(quantity)
        / dialogue_mode
        / TABLES
        / "NMS_DIALOG_GCALIENPUZZLETABLE.EXML"
    )
    default_root = ET.parse(default_path).getroot()
    replace_autophage_entries(
        default_root,
        quantity,
        *DEFAULT_AUTOPHAGE_SETTINGS,
    )
    write_xml(default_path, default_root)

    for multiplier in MULTIPLIER_MODES:
        for dialogue_behavior in AUTOPHAGE_DIALOGUE_MODES:
            if (multiplier, dialogue_behavior) == DEFAULT_AUTOPHAGE_SETTINGS:
                continue
            variant_root = copy.deepcopy(default_root)
            replace_autophage_entries(
                variant_root,
                quantity,
                multiplier,
                dialogue_behavior,
            )
            variant_path = (
                FOMOD
                / "autophage-dialogue"
                / multiplier
                / dialogue_behavior
                / str(quantity)
                / dialogue_mode
                / TABLES
                / "NMS_DIALOG_GCALIENPUZZLETABLE.EXML"
            )
            write_xml(variant_path, variant_root)


def plugin(
    name: str,
    description: str,
    flag_name: str,
    flag_value: str,
    type_name: str,
    image_path: str | None = None,
) -> ET.Element:
    element = ET.Element("plugin", {"name": name})
    ET.SubElement(element, "description").text = description
    if image_path is not None:
        ET.SubElement(element, "image", {"path": image_path})
    flags = ET.SubElement(element, "conditionFlags")
    flag = ET.SubElement(flags, "flag", {"name": flag_name})
    flag.text = flag_value
    descriptor = ET.SubElement(element, "typeDescriptor")
    ET.SubElement(descriptor, "type", {"name": type_name})
    return element


def append_autophage_step(install_steps: ET.Element) -> None:
    autophage_step = ET.SubElement(
        install_steps,
        "installStep",
        {"name": "Autophage Settings"},
    )
    groups = ET.SubElement(autophage_step, "optionalFileGroups", {"order": "Explicit"})

    multiplier_group = ET.SubElement(
        groups,
        "group",
        {"name": "Autophage Gift Multiplier", "type": "SelectExactlyOne"},
    )
    multiplier_plugins = ET.SubElement(
        multiplier_group,
        "plugins",
        {"order": "Explicit"},
    )
    multiplier_plugins.append(
        plugin(
            "Enable Multiplier",
            "Apply the selected gift amount to Autophage gift costs and standing rewards.",
            "autophage_multiplier",
            "enabled",
            "Recommended",
            image_path="fomod/images/autophage-10.jpg",
        )
    )
    multiplier_plugins.append(
        plugin(
            "Disable Multiplier",
            "Leave Autophage gift costs and standing rewards at their vanilla amounts.",
            "autophage_multiplier",
            "disabled",
            "Optional",
            image_path="fomod/images/autophage-multiplier-disabled.jpg",
        )
    )

    dialogue_group = ET.SubElement(
        groups,
        "group",
        {"name": "Autophage Dialogue Behavior", "type": "SelectExactlyOne"},
    )
    dialogue_plugins = ET.SubElement(
        dialogue_group,
        "plugins",
        {"order": "Explicit"},
    )
    dialogue_plugins.append(
        plugin(
            "Keep dialogue open and cycle gift option",
            "Keep the dialogue open and reseed the Autophage to request another gift after each gift.",
            "autophage_dialogue",
            "keep",
            "Recommended",
            image_path="fomod/images/autophage-dialogue-open.gif",
        )
    )
    dialogue_plugins.append(
        plugin(
            "Close dialogue and remove ability to regift that NPC (normal behavior)",
            "Use vanilla behavior: close the dialogue and remove the gift option for that Autophage.",
            "autophage_dialogue",
            "remove",
            "Optional",
            image_path="fomod/images/autophage-dialogue-closed.gif",
        )
    )


def update_module_config() -> None:
    path = FOMOD / "ModuleConfig.xml"
    root = ET.parse(path).getroot()
    install_steps = root.find("installSteps")
    if install_steps is None:
        raise SystemExit("ModuleConfig.xml is missing installSteps.")
    first_step = install_steps.find("installStep")
    if first_step is None:
        raise SystemExit("ModuleConfig.xml is missing its primary installStep.")
    first_step.set("name", "Gek, Korvax, and Vy'keen Settings")
    quantity_descriptions = {
        str(quantity): (
            f"Give {quantity} gifts and receive {quantity} standing. This amount also "
            "controls the Autophage multiplier when enabled on the next page."
        )
        for quantity in QUANTITIES
    }
    for group in first_step.findall("./optionalFileGroups/group"):
        flag_names = {
            flag.get("name")
            for flag in group.findall("./plugins/plugin/conditionFlags/flag")
        }
        if "gift_amount" in flag_names:
            group.set("name", "Choose an Exact Amount")
        elif "dialogue_mode" in flag_names:
            group.set("name", "Dialogue Behavior")

    for option in first_step.findall("./optionalFileGroups/group/plugins/plugin"):
        description = option.find("description")
        if description is None:
            raise SystemExit("A primary FOMOD option is missing its description.")
        gift_amount = option.find("./conditionFlags/flag[@name='gift_amount']")
        dialogue_flag = option.find("./conditionFlags/flag[@name='dialogue_mode']")
        if gift_amount is not None and gift_amount.text in quantity_descriptions:
            description.text = quantity_descriptions[gift_amount.text]
        elif dialogue_flag is not None and dialogue_flag.text == "open":
            option.set("name", "Keep Dialogue Open")
            description.text = (
                "Leave Gek, Korvax, and Vy'keen dialogue open after giving a gift."
            )
            image = option.find("image")
            if image is None:
                image = ET.Element("image")
                option.insert(1, image)
            image.set("path", "fomod/images/normal-dialogue-open.gif")
        elif dialogue_flag is not None and dialogue_flag.text == "closed":
            option.set("name", "Close dialogue (normal behavior)")
            description.text = (
                "Close Gek, Korvax, and Vy'keen dialogue after giving a gift."
            )
            image = option.find("image")
            if image is None:
                image = ET.Element("image")
                option.insert(1, image)
            image.set("path", "fomod/images/normal-dialogue-closed.gif")
    for step in list(install_steps):
        if step is not first_step:
            install_steps.remove(step)

    append_autophage_step(install_steps)

    conditional = root.find("conditionalFileInstalls")
    if conditional is None:
        conditional = ET.SubElement(root, "conditionalFileInstalls")
    patterns = conditional.find("patterns")
    if patterns is None:
        patterns = ET.SubElement(conditional, "patterns")
    patterns.clear()
    for quantity in QUANTITIES:
        for dialogue_mode in DIALOGUE_MODES:
            for multiplier in MULTIPLIER_MODES:
                for autophage_dialogue in AUTOPHAGE_DIALOGUE_MODES:
                    pattern = ET.SubElement(patterns, "pattern")
                    dependencies = ET.SubElement(
                        pattern, "dependencies", {"operator": "And"}
                    )
                    for flag, value in (
                        ("gift_amount", str(quantity)),
                        ("dialogue_mode", dialogue_mode),
                        ("autophage_multiplier", multiplier),
                        ("autophage_dialogue", autophage_dialogue),
                    ):
                        ET.SubElement(
                            dependencies,
                            "flagDependency",
                            {"flag": flag, "value": value},
                        )
                    files = ET.SubElement(pattern, "files")
                    if (multiplier, autophage_dialogue) == DEFAULT_AUTOPHAGE_SETTINGS:
                        source = f"fomod/dialogue/{quantity}/{dialogue_mode}"
                    else:
                        source = (
                            "fomod/autophage-dialogue/"
                            f"{multiplier}/{autophage_dialogue}/{quantity}/{dialogue_mode}"
                        )
                    ET.SubElement(
                        files,
                        "folder",
                        {
                            "source": source,
                            "destination": "GAMEDATA/MODS/GenerousGiver",
                        },
                    )
    write_xml(path, root)


def main() -> None:
    if len(sys.argv) != 1:
        raise SystemExit("Usage: generate_fomod_payloads.py")
    for quantity in QUANTITIES:
        update_quantity_tables(quantity)
        for dialogue_mode in DIALOGUE_MODES:
            update_dialogue_payloads(quantity, dialogue_mode)
    update_module_config()
    print("Generated Autophage payloads for all FOMOD configurations.")


if __name__ == "__main__":
    main()
