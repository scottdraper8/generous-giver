# Implementation contract

## Product behavior

The player selects one **Offer a gift** action while talking to an alien. The action gives up to the configured limit in one interaction, taking only compatible items from inventories the game considers accessible to that interaction. For a limit of 10, seven accessible gifts means seven are offered; eleven means ten. **All** offers the full compatible amount currently accessible. Other choices and non-gift costs must remain unchanged.

The installer exposes exactly one of 5x, 10x, or All. The choice applies to all supported alien gift tiers/races; it is not a choice between races.

## Data boundary observed locally

The installed No Man's Sky Steam app manifest reported build `26295378`. The matching community MBINCompiler release available during this investigation was `v7.10.0-pre1`. This is an investigation snapshot, not a compatibility promise for a release.

The relevant vanilla asset paths are:

- `METADATA/REALITY/TABLES/NMS_DIALOG_GCALIENPUZZLETABLE.MBIN` — alien interaction options and references to costs.
- `METADATA/REALITY/TABLES/COSTTABLE.MBIN` — shared costs for dialogue options.

The gift-tier cost IDs found in the current cost table are `KORVAXGIFT1`, `KORVAXGIFT2`, `GEKGIFT1`, `GEKGIFT2`, `VYKGIFT1`, and `VYKGIFT2`. They map to the race-specific Curio product IDs and currently specify an amount of one. The same cost IDs occur in more than one dialogue context. A global amount change may therefore affect purchases, salvage, or other offers; references must be classified before patching. See the [cost-reference investigation](cost-reference-investigation.md) for the observed reference counts and unresolved runtime questions.

These findings were made from local vanilla data and must be rechecked against the game build selected for release. No extracted game data is stored in this repository.

## Unresolved implementation gate

A cost amount may be a fixed affordability requirement, not a maximum. If a cost of ten disables the action when only seven items are available, changing that scalar cannot implement the required up-to behavior. Likewise, a very large scalar is not an acceptable implementation of All unless the game is proven to consume the accessible quantity without requiring that entire scalar.

Before adding any runtime patch, establish the native interaction's exact behavior and narrowest safe data seam. If the native data path cannot satisfy the contract, stop and report that limitation rather than shipping a misleading 5x/10x/All installer or broadening the mod without review.

## Acceptance checks before release

1. Record the exact public game version, Steam build ID, and matching MBINCompiler identity. Refresh affected assets from that build.
2. Identify every dialogue option that represents gifting to an alien and every use of its cost IDs. Prove unrelated options are unchanged.
3. Prove which inventory sources the native dialogue can access. Test player, ship, freighter, and any other inventory only if the game exposes it for that interaction; do not assume access from storage UI behavior.
4. For each race and gift tier, test zero items, one item, fewer items than the selected cap, exactly the cap, and more than the cap.
5. Verify the quantity removed equals the quantity accepted, and verify reward/standing behavior occurs once with the intended total.
6. Exercise the FOMOD's 5x, 10x, and All selections and inspect each installed output tree for the correct mod root and no unintended files.
7. Validate EXML parsing and target paths; then validate merged game metadata and behavior in a disposable/backed-up save under controlled conditions.
8. Check mod conflicts with overlapping dialogue/cost patches and report tested compatibility precisely.
9. Run the complete pre-commit/CI suite and review the final package for secrets, unrelated files, and accidental game-data redistribution.

No release is acceptable while a required behavior is unknown or only inferred from XML structure.
