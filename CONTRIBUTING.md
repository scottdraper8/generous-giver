# Contributing

## Set up

Use Python 3.13.18. Install the fully pinned tooling in a virtual environment and register the local Git hook:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements.txt
source .venv/bin/activate
pre-commit install
```

## Before opening or updating a pull request

Run the same checks CI uses:

```sh
pre-commit run --all-files --show-diff-on-failure
```

All repository checks are required. Do not bypass them with skip variables, inline suppressions, disabled Git hooks, or verification-bypass flags. A failed check is a defect to fix, not a reason to skip the check. CI reruns the complete suite independently, so local hook installation is not the only enforcement point.

## Mod validation

This repository is not yet an installable mod. Keep extracted game data and disposable-save test material outside Git. Before adding runtime patches, document the exact game build and prove that gift costs consume up to the selected cap from the inventories visible to the NPC interaction. Test the 5x, 10x, and All choices, including fewer items than the selected cap. Follow the complete acceptance list in [the implementation contract](docs/implementation-contract.md).

## Dependencies and CI

Pin dependencies to exact versions and hashes where supported. GitHub Actions must use reviewed full commit SHAs, not mutable tags. Dependabot may open dependency/security pull requests; it must not auto-merge them. Security and quality changes must preserve the required CI gate.
