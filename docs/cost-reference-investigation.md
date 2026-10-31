# Native alien-gift cost reference investigation

## Snapshot and limits

This is a read-only analysis of the local No Man's Sky Steam data snapshot, build `26295378`. It used the converted MXML tables listed below; no game data, binaries, saves, or extracted assets are included in this repository. The converted files and conversion log identify the MBINCompiler binary as `7.10.0.1`; the implementation contract records the corresponding community release as `v7.10.0-pre1`. Reconcile and record the exact tool identity when refreshing the data for a release build.

- `METADATA/REALITY/TABLES/COSTTABLE.MBIN`
- `METADATA/REALITY/TABLES/NMS_DIALOG_GCALIENPUZZLETABLE.MBIN`

## Shared cost definitions

All six race/tier cost IDs have a `GcCostProduct` with an explicit amount of `1`, `UseDefaultAmount=false`, and `TakeIDFromSeasonData=false`:

| Cost ID | Product ID | Tier |
| --- | --- | --- |
| `GEKGIFT1` | `TRA_CURIO1` | Gek 1 |
| `GEKGIFT2` | `TRA_CURIO2` | Gek 2 |
| `KORVAXGIFT1` | `EXP_CURIO1` | Korvax 1 |
| `KORVAXGIFT2` | `EXP_CURIO2` | Korvax 2 |
| `VYKGIFT1` | `WAR_CURIO1` | Vy'keen 1 |
| `VYKGIFT2` | `WAR_CURIO2` | Vy'keen 2 |

This describes the serialized data only. It does not prove how the game checks affordability, which inventory containers it searches, or how much it removes after a successful choice.

## Screenshot target and structural limit

The supplied reference screenshot identifies the Korvax secondary interaction, `EXP_NPC_SECONDARY`, and its highlighted **Offer a gift** option. In the converted table, this option is `Name=ALL_REQUEST_STD_LOW`, `Text=ALL_REPLY_STANDING`, `Cost=KORVAXGIFT1`, and `Rewards=SEC_STDLOW_EXP`. The entry's prompt text is `EXP_REQUEST_DESC_1`. The same table ID occurs 49 times in this asset as repeated entries/variants; that is not a count of unique gameplay encounters.

`KORVAXGIFT1` is the shared cost ID for product `EXP_CURIO1` (Korvax Casing), with one fixed `Amount` and `UseDefaultAmount=false` / `TakeIDFromSeasonData=false`. The dialogue option refers to that cost by ID; it has no per-option quantity expression. The serialized cost fields inspected here contain no selector for a maximum, `min(available, cap)`, or all currently accessible items. `UseDefaultAmount` and `TakeIDFromSeasonData` are not inventory-count selectors. The format therefore gives no data-only way to express the requested up-to behavior or All. This is a structural finding, not proof of how the native runtime interprets a fixed amount; no controlled game test has established special runtime behavior.

The target scope is only this Korvax option. Do not alter `KORVAXGIFT1` globally or expand the patch to other races/tiers. If native runtime semantics are later proven, isolate changes to the target option across its repeated entries and keep sibling dialogue and the shared cost definition intact.

## Dialogue references

A read-only parse of `NMS_DIALOG_GCALIENPUZZLETABLE.MBIN` found the following `Cost` reference counts and distinct dialogue table IDs. Counts include repeated table variants in the converted file; they are not counts of unique gameplay encounters.

| Cost ID | References | Distinct table IDs |
| --- | ---: | ---: |
| `GEKGIFT1` | 59 | 5 |
| `GEKGIFT2` | 8 | 3 |
| `KORVAXGIFT1` | 60 | 4 |
| `KORVAXGIFT2` | 9 | 4 |
| `VYKGIFT1` | 53 | 6 |
| `VYKGIFT2` | 10 | 5 |

The references span normal, secondary, and outlaw dialogue as well as special tables. Examples include `NPC_HAILED_OFFER_GOODS`, `TRA_NPC_SHOP_1`, crash-site and scavenger tables, and `WAR_FACTORY3`. Some options also award mission, item, or standing rewards. Therefore, changing a shared cost definition globally is not a safe way to change only the intended gift action. Each target option must be classified, and unrelated dialogue costs and rewards must be preserved.

## Release gate remains open

- The inspected data schema contains only a fixed cost amount, not an explicit `min(available, cap)` or All operation. The loose-data implementation is blocked unless native runtime semantics are independently proven to supply the missing behavior.
- The inspected interaction/cost data does not establish whether costs are drawn from the exosuit only, the active ship, freighter storage, or another game-accessible inventory.
- No controlled in-game tests have been run for below-cap quantities, exact-cap quantities, above-cap quantities, removed quantities, rewards, or standing.

Keep the FOMOD payload lists empty and do not describe the repository as installable. Runtime affordability, inventory-source, under-cap, exact-cap, above-cap, removal, and reward behavior remain untested against a recorded game build. Follow the acceptance checks in [the implementation contract](implementation-contract.md).
