# Generous Giver

A No Man's Sky data mod intended to let a player offer multiple eligible gifts to an alien in one interaction. The FOMOD is planned to offer **5x**, **10x**, and **All** limits.

> **Development scaffold only — not an installable or release-ready mod.** The FOMOD currently defines the settings screen but contains no game payload. The amount/cost behavior and the `All` mode must be validated against the current game before any payload is added or distributed.

## Intended behavior

- Extend the existing alien gift interaction rather than add an unrelated menu or runtime hook.
- Offer up to the selected cap from the inventories the game makes available to that interaction. If the selected cap is 10 and the game can see 7 compatible gifts, offer 7; if it can see 11, offer 10.
- `All` means all compatible gifts currently available to that interaction.
- Leave all non-gift actions and unrelated costs unchanged.
- Ship a FOMOD installer with mutually exclusive 5x, 10x, and All choices.
- Prefer a narrow loose-data patch. No DLL, executable injection, or extra runtime process is part of the design.

## Current investigation

The current local game data exposes the alien dialogue in `METADATA/REALITY/TABLES/NMS_DIALOG_GCALIENPUZZLETABLE.MBIN` and item costs in `METADATA/REALITY/TABLES/COSTTABLE.MBIN`. Cost IDs include the Gek, Korvax, and Vy'keen gift tiers. Those costs are referenced outside the simple gift prompt too, so changing their shared definitions blindly could alter unrelated interactions.

See [the implementation contract](docs/implementation-contract.md) for the verified data boundary and the remaining acceptance checks. No game assets, extracted tables, saves, or compiler binaries are included here.

## Development

Requirements:

- Python 3.13.18 for repository checks
- `pre-commit`, Ruff, and pip-audit with exact versions and hashes in [`requirements.txt`](requirements.txt)

Set up and run all checks (commands shown for Linux/macOS):

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements.txt
source .venv/bin/activate
pre-commit install
pre-commit run --all-files
```

The hooks include repository-specific FOMOD, dependency-pin, policy, XML, and test checks. CI runs the same full hook suite on every push and pull request. See [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md) for the non-bypassable development rules.

## Installation and compatibility

There is no working mod payload to install yet. Do not install this repository into a game or publish it as a mod until the acceptance checks in the implementation contract pass. No Man's Sky is an unsupported, update-sensitive modding target; compatibility must be stated against a tested game build rather than inferred from a successful XML parse.

## Ownership

No Man's Sky, its data, and its assets belong to Hello Games. This repository does not include redistributed game data. The repository's own licensing terms have not yet been selected.
