#!/usr/bin/env python3
"""Repository-specific quality and anti-bypass checks (Python standard library only)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".xml",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".txt",
    ".cfg",
    ".sh",
    ".ps1",
    ".bat",
    ".cmd",
}
POLICY_DOCS = {"AGENTS.md", "CONTRIBUTING.md"}

# Keep this scanner intentionally focused on suppression directives, not normal code comments.
SUPPRESSIONS = (
    re.compile(
        r"(?im)^\s*#\s*(?:noqa\b|type\s*:\s*ignore\b|fmt\s*:\s*off\b|pylint\s*:\s*disable\b|mypy\s*:\s*ignore\b|pyright\s*:\s*ignore\b|pragma\s*:\s*no\s+cover\b|nosec\b)"
    ),
    re.compile(r"(?im)^\s*//\s*(?:nolint\b|eslint-disable\b|prettier-ignore\b)"),
    re.compile(
        r"(?is)<!--\s*(?:noinspection\b|eslint-disable\b|prettier-ignore\b|stylelint-disable\b)"
    ),
)
BYPASSES = (
    re.compile("-" * 2 + r"no-verify", re.IGNORECASE),
    re.compile(r"(?im)^\s*(?:export\s+)?SKIP\s*="),
    re.compile(r"(?i)PRE_COMMIT_ALLOW_NO_CONFIG"),
    re.compile(r"(?i)core\.hooksPath"),
)
ACTION_USE = re.compile(
    r"^\s*uses:\s*([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@([0-9a-fA-F]+)\s+#\s+(v\S+)\s*$"
)
PIN_LINE = re.compile(r"^([A-Za-z0-9_.-]+)==([A-Za-z0-9][A-Za-z0-9.!+_-]*)\\?$", re.IGNORECASE)
HASH_LINE = re.compile(r"^--hash=sha256:[0-9a-f]{64}$", re.IGNORECASE)


def repository_files() -> list[Path]:
    listing = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if listing.returncode == 0:
        candidates = [ROOT / item.decode("utf-8") for item in listing.stdout.split(b"\0") if item]
    else:
        ignored = {
            ".git",
            ".venv",
            "venv",
            "node_modules",
            "build",
            "dist",
            "out",
            "target",
            "__pycache__",
        }
        candidates = [
            path
            for path in ROOT.rglob("*")
            if path.is_file() and not ignored.intersection(path.relative_to(ROOT).parts)
        ]
    return sorted(
        path
        for path in candidates
        if path.is_file()
        and (
            path.suffix.lower() in TEXT_SUFFIXES
            or path.name in {".gitignore", ".gitattributes", ".pre-commit-config.yaml"}
        )
    )


def hygiene_issues(paths: list[Path] | None = None) -> list[str]:
    issues: list[str] = []
    for path in paths if paths is not None else repository_files():
        label = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            issues.append(f"{label}: text file is not valid UTF-8")
            continue
        except OSError as exc:
            issues.append(f"{label}: cannot read file: {exc}")
            continue

        if b"\r" in raw:
            issues.append(f"{label}: CR/CRLF line ending found; use LF")
        if raw and not raw.endswith(b"\n"):
            issues.append(f"{label}: missing final newline")
        for line_number, line in enumerate(text.splitlines(), 1):
            if line.rstrip(" \t") != line:
                issues.append(f"{label}:{line_number}: trailing whitespace")
        for conflict in re.finditer(r"(?m)^(?:<<<<<<< |=======$|>>>>>>> )", text):
            line_number = text.count("\n", 0, conflict.start()) + 1
            issues.append(f"{label}:{line_number}: merge-conflict marker found")
        if path.suffix.lower() == ".json":
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:
                issues.append(f"{label}: invalid JSON: {exc}")
        if path.suffix.lower() == ".toml":
            try:
                tomllib.loads(text)
            except tomllib.TOMLDecodeError as exc:
                issues.append(f"{label}: invalid TOML: {exc}")
        if path.suffix.lower() in {".yml", ".yaml"}:
            try:
                yaml.safe_load(text)
            except yaml.YAMLError as exc:
                issues.append(f"{label}: invalid YAML: {exc}")
        if path.suffix.lower() == ".xml":
            if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
                issues.append(f"{label}: DTD and entity declarations are not permitted")
            else:
                try:
                    ET.fromstring(text)
                except ET.ParseError as exc:
                    issues.append(f"{label}: invalid XML: {exc}")
    return issues


def fomod_issues() -> list[str]:
    issues: list[str] = []
    config_path = ROOT / "fomod" / "ModuleConfig.xml"
    info_path = ROOT / "fomod" / "info.xml"
    try:
        config = ET.parse(config_path).getroot()
        info = ET.parse(info_path).getroot()
    except (ET.ParseError, OSError) as exc:
        return [f"FOMOD metadata cannot be parsed: {exc}"]

    if config.tag != "config":
        issues.append("fomod/ModuleConfig.xml: root element must be <config>")
    if config.findtext("moduleName") != "Generous Giver":
        issues.append("FOMOD module name must be Generous Giver")
    groups = config.findall("./installSteps/installStep/optionalFileGroups/group")
    if len(groups) != 1 or groups[0].get("type") != "SelectExactlyOne":
        issues.append("FOMOD must present one mutually exclusive gift-limit group")
    else:
        names = [plugin.get("name") for plugin in groups[0].findall("./plugins/plugin")]
        if names != ["5x", "10x", "All"]:
            issues.append("FOMOD choices must be exactly 5x, 10x, All in that order")
        descriptions = {
            plugin.get("name"): plugin.findtext("description", "")
            for plugin in groups[0].findall("./plugins/plugin")
        }
        if "up to five" not in descriptions.get("5x", ""):
            issues.append("5x must be described as an up-to cap")
        if "up to ten" not in descriptions.get("10x", ""):
            issues.append("10x must be described as an up-to cap")
        if "all compatible gifts" not in descriptions.get("All", ""):
            issues.append("All must describe the accessible compatible gifts")
        for name, description in descriptions.items():
            if "targeted Korvax gift interaction" not in description:
                issues.append(
                    f"FOMOD {name} must stay scoped to the targeted Korvax gift interaction"
                )
        for plugin in groups[0].findall("./plugins/plugin"):
            if plugin.find("files") is None or list(plugin.find("files")):
                issues.append(
                    f"FOMOD {plugin.get('name')} files must stay empty until the "
                    "payload is validated"
                )

    if info.tag != "fomod" or info.findtext("Name") != "Generous Giver":
        issues.append("fomod/info.xml must identify the Generous Giver package")
    version = info.findtext("Version", "")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        issues.append("FOMOD package version must be exact numeric semver")
    if (ROOT / "fomod" / "files").exists():
        issues.append(
            "FOMOD payload directory must not exist before native gift behavior is validated"
        )
    return issues


def pin_issues() -> list[str]:
    issues: list[str] = []
    workflow_paths = sorted((ROOT / ".github" / "workflows").glob("*.yml")) + sorted(
        (ROOT / ".github" / "workflows").glob("*.yaml")
    )
    action_count = 0
    for path in workflow_paths:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.match(r"^\s*uses\s*:", line):
                action_count += 1
                match = ACTION_USE.match(line)
                if match is None or len(match.group(2)) != 40:
                    issues.append(
                        f"{path.relative_to(ROOT)}:{number}: GitHub Action must use a full "
                        "commit SHA and reviewed version comment"
                    )
    if action_count == 0:
        issues.append("No pinned GitHub Actions were found")

    requirements = ROOT / "requirements.txt"
    if not requirements.exists():
        return issues + ["requirements.txt hash lock is missing"]
    package_count = 0
    pre_commit_pins: list[str] = []
    current_has_hash = False
    for number, raw_line in enumerate(requirements.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("--hash="):
            hash_line = line.removesuffix("\\").rstrip()
            if not HASH_LINE.fullmatch(hash_line):
                issues.append(f"requirements.txt:{number}: hash must be a SHA-256 digest")
            current_has_hash = True
            continue
        if line.startswith("--"):
            issues.append(f"requirements.txt:{number}: unreviewed pip option is not allowed")
            continue
        package_line = line.removesuffix("\\").rstrip()
        if not PIN_LINE.fullmatch(package_line):
            issues.append(f"requirements.txt:{number}: dependency must use an exact == version")
        pre_commit_match = re.fullmatch(r"(?i)pre[-_]commit==(\d+\.\d+\.\d+)", package_line)
        if pre_commit_match is not None:
            pre_commit_pins.append(pre_commit_match.group(1))
        if package_count and not current_has_hash:
            issues.append(f"requirements.txt:{number}: previous dependency has no SHA-256 hash")
        package_count += 1
        current_has_hash = False
    if package_count and not current_has_hash:
        issues.append("requirements.txt: final dependency has no SHA-256 hash")
    if package_count == 0:
        issues.append("requirements.txt must pin at least the pre-commit toolchain")
    if len(pre_commit_pins) != 1:
        issues.append("requirements.txt must contain exactly one exact pre-commit pin")
    else:
        pre_commit_config = ROOT / ".pre-commit-config.yaml"
        try:
            config = yaml.safe_load(pre_commit_config.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            issues.append(f".pre-commit-config.yaml cannot be checked: {exc}")
        else:
            minimum_version = (
                config.get("minimum_pre_commit_version") if isinstance(config, dict) else None
            )
            if not isinstance(minimum_version, str) or not re.fullmatch(
                r"\d+\.\d+\.\d+", minimum_version
            ):
                issues.append(
                    ".pre-commit-config.yaml must specify an exact minimum_pre_commit_version"
                )
            else:
                locked_parts = tuple(int(part) for part in pre_commit_pins[0].split("."))
                minimum_parts = tuple(int(part) for part in minimum_version.split("."))
                if locked_parts < minimum_parts:
                    issues.append(
                        "requirements.txt pre-commit pin "
                        f"{pre_commit_pins[0]} is below .pre-commit-config.yaml minimum "
                        f"{minimum_version}"
                    )
    return issues


def policy_issues() -> list[str]:
    issues: list[str] = []
    for path in repository_files():
        relative = path.relative_to(ROOT)
        if relative.as_posix() in POLICY_DOCS or relative.as_posix() == "scripts/quality.py":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for pattern in BYPASSES:
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                issues.append(f"{relative}:{line}: hook-bypass mechanism is forbidden")
                break
        for pattern in SUPPRESSIONS:
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                issues.append(
                    f"{relative}:{line}: inline lint/format/test suppression is forbidden"
                )
                break
    return issues


def run_check(name: str) -> int:
    checks = {
        "hygiene": hygiene_issues,
        "fomod": fomod_issues,
        "pins": pin_issues,
        "policy": policy_issues,
    }
    failures = checks[name]()
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"{name}: passed")
    return 0


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"hygiene", "fomod", "pins", "policy"}:
        print("Usage: python3 scripts/quality.py {hygiene|fomod|pins|policy}", file=sys.stderr)
        return 2
    return run_check(sys.argv[1])


if __name__ == "__main__":
    raise SystemExit(main())
