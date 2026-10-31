# Implementation contract

## Product behavior

Target only the Korvax **Offer a gift** choice shown in the project reference: the `EXP_NPC_SECONDARY` interaction's `ALL_REQUEST_STD_LOW` option. Do not change the adjacent language-practice or leave choices, other races, other gift tiers, shared cost definitions, rewards, or progression.

The intended action gives up to the selected limit in one interaction, taking only Korvax Casing items from inventories the game makes accessible to that interaction. For a limit of 10, seven accessible items means seven are offered; eleven means ten. **All** offers the full compatible amount currently accessible. The installer exposes exactly one of 5x, 10x, or All, scoped only to this target choice.

## Data boundary observed locally

The installed No Man's Sky Steam app manifest reported build `26295378`. The matching community MBINCompiler release available during this investigation was `v7.10.0-pre1`. This is an investigation snapshot, not a compatibility promise for a release.

The relevant vanilla asset paths are:

- `METADATA/REALITY/TABLES/NMS_DIALOG_GCALIENPUZZLETABLE.MBIN` — alien interaction options and references to costs.
- `METADATA/REALITY/TABLES/COSTTABLE.MBIN` — shared costs for dialogue options.

The screenshot target maps to `EXP_NPC_SECONDARY` / `ALL_REQUEST_STD_LOW`, with `Cost=KORVAXGIFT1` and `Rewards=SEC_STDLOW_EXP`. `KORVAXGIFT1` is a shared cost-table ID for product `EXP_CURIO1` and has a fixed `Amount=1`; other options also reference it. Do not change that shared definition globally. See the [cost-reference investigation](cost-reference-investigation.md) for the exact serialized fields and reference counts.

These findings were made from local vanilla data and must be rechecked against the game build selected for release. No extracted game data is stored in this repository.

## Unresolved implementation gate

The inspected serialized data provides no dynamic maximum, available-inventory quantity, or All selector: the dialogue option names one cost ID, and its cost entry contains a fixed product ID and amount. `UseDefaultAmount` and `TakeIDFromSeasonData` do not encode a per-interaction inventory count. A 5 or 10 in that amount field is therefore only a fixed scalar in the data; no asset field establishes the required `min(available, cap)`, and no value expresses All. The runtime could have special semantics for the scalar, but none have been demonstrated here.

This is enough to block the current loose-data-only design. Keep the payload empty and do not substitute an exact 5/10 cost or a large sentinel for the promised behavior. If future evidence establishes native runtime support, revisit the narrow target option. Do not add a DLL, executable hook, or helper under the current contract; report the limitation instead of broadening the implementation.

## Acceptance checks before release

1. Record the exact public game version, Steam build ID, and matching MBINCompiler identity. Refresh affected assets from that build.
2. Classify the target `ALL_REQUEST_STD_LOW` option across the repeated `EXP_NPC_SECONDARY` entries and prove all sibling options and shared cost definitions are unchanged.
3. Prove which inventory sources this exact interaction can access; do not assume access from storage UI behavior.
4. For the Korvax gift choice, test zero, one, fewer than the selected cap, exactly the cap, and more than the cap for 5x, 10x, and All.
5. Verify the quantity removed equals the quantity accepted, and verify the `SEC_STDLOW_EXP` reward/standing behavior occurs once with the intended total.
6. Exercise the FOMOD's 5x, 10x, and All selections and inspect each installed output tree for the correct mod root and no unintended files.
7. Validate EXML parsing and target paths; then validate merged game metadata and behavior in a disposable/backed-up save under controlled conditions.
8. Check mod conflicts with overlapping dialogue/cost patches and report tested compatibility precisely.
9. Run the complete pre-commit/CI suite and review the final package for secrets, unrelated files, and accidental game-data redistribution.

No release is acceptable while a required behavior is unknown or only inferred from XML structure.
