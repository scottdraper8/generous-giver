#!/usr/bin/env python3
"""Enforce immutable tools and security-only dependency updates."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
ACTION_REFERENCE = re.compile(r"^\s*uses:\s*([^\s#]+)@([^\s#]+)", re.MULTILINE)
PRECOMMIT_REFERENCE = re.compile(
    r"^\s*-\s+repo:\s*(?!local\s*$)\S+.*?^\s+rev:\s*([^\s#]+)",
    re.MULTILINE | re.DOTALL,
)
NODE_DEPENDENCY = re.compile(r"^[a-z0-9@/_.-]+@[0-9]+\.[0-9]+\.[0-9]+$")


def main() -> int:
    failures: list[str] = []
    for workflow in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        for action, revision in ACTION_REFERENCE.findall(
            workflow.read_text(encoding="utf-8")
        ):
            if (
                not action.startswith(("./", "docker://"))
                and SHA40.fullmatch(revision) is None
            ):
                failures.append(
                    f"{workflow.relative_to(ROOT)}: {action} must use a full commit SHA"
                )

    precommit = ROOT / ".pre-commit-config.yaml"
    precommit_text = precommit.read_text(encoding="utf-8")
    for revision in PRECOMMIT_REFERENCE.findall(precommit_text):
        if SHA40.fullmatch(revision) is None:
            failures.append(
                f"{precommit.relative_to(ROOT)}: hook revision {revision!r} is not a full commit SHA"
            )
    for line in precommit_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("additional_dependencies:"):
            dependencies = stripped.partition(":")[2].strip().strip("[]")
            for dependency in (item.strip() for item in dependencies.split(",")):
                if dependency and NODE_DEPENDENCY.fullmatch(dependency) is None:
                    failures.append(
                        f"{precommit.relative_to(ROOT)}: {dependency!r} is not exactly versioned"
                    )

    dependabot = ROOT / ".github" / "dependabot.yml"
    dependabot_text = dependabot.read_text(encoding="utf-8")
    for ecosystem in ("github-actions",):
        if dependabot_text.count(f"package-ecosystem: {ecosystem}") != 1:
            failures.append(f"Dependabot must monitor {ecosystem} exactly once")
    if dependabot_text.count("open-pull-requests-limit: 0") != 1:
        failures.append("Dependabot routine version-update PRs must be disabled")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
