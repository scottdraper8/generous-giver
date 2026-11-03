# Agent instructions

## Product contract

- Build **Generous Giver** as a No Man's Sky loose-data mod targeting only the Korvax **Offer a gift** choice in the pictured secondary interaction (`EXP_NPC_SECONDARY` / `ALL_REQUEST_STD_LOW`). The installer choices are 5x, 10x, and All.
- A cap means *up to* the selected amount. If only seven compatible gifts are accessible at a cap of ten, the game must offer those seven rather than disable the action. All means the complete compatible amount visible to the game at that interaction.
- Use only the inventories the game itself makes available to this interaction. Do not invent an inventory search or promise access to storage that the game cannot reach.
- Preserve every sibling dialogue option, shared cost, reward, and progression effect. Do not broaden the target to other races or gift tiers.
- Prefer the narrowest native data patch. Do not add DLLs, executable hooks, or a runtime helper unless investigation proves the data-only design cannot meet the contract; if so, stop and report the incompatibility instead of weakening the behavior silently.
- Do not put extracted game files, copyrighted assets, saves, local logs, or compiler binaries in this repository.
- Keep this project independent of the `squinchmods` worktree. Never modify its active submodules, probes, or agents' changes while working here.

## Mandatory quality gate

- Run `pre-commit run --all-files` before declaring work complete. CI must remain green.
- Never skip, suppress, disable, or weaken a pre-commit hook. No inline lint/format/test suppressions, `SKIP` overrides, hook-path bypasses, or verification bypass flags are allowed.
- Do not use blanket exclusions to make a hook pass. Fix the underlying issue, or revise a rule only when its existing contract is demonstrably wrong and add a test for the corrected rule.
- Keep all direct and transitive dependencies exactly pinned. Pin GitHub Actions to full commit SHAs and update the version comment with the reviewed release.
- Do not claim the mod is ready until the tested game build, inventory-source behavior, under-cap behavior, all-inventory behavior, and all three installer choices pass the acceptance checks in `docs/implementation-contract.md`.

## Durable context

The repo is intentionally a pre-release scaffold: the FOMOD describes the three settings, but no game patch is shipped yet. The inspected native data stores a fixed product amount and has no explicit maximum, available-quantity, or All selector. Runtime semantics have not been tested, so do not turn a fixed exact cost into an up-to cap or populate the payload without evidence.
