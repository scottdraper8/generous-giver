#!/usr/bin/env python3
"""Resolve existing Nexus file entries and avoid duplicate version uploads."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote


API_BASE = "https://api.nexusmods.com/v3"
MOD_ID = "7017976566438"


def get_json(path: str, api_key: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{API_BASE}{path}",
        headers={
            "Accept": "application/json",
            "User-Agent": "Generous-Giver release workflow",
            "apikey": api_key,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return cast(dict[str, Any], json.load(response))
    except urllib.error.HTTPError as error:
        raise SystemExit(
            f"Nexus API request failed with HTTP {error.code}: {path}"
        ) from None
    except urllib.error.URLError as error:
        raise SystemExit(f"Nexus API request failed: {error.reason}") from None


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: resolve_nexus_files.py RELEASE_ASSET_MANIFEST")

    api_key = os.environ.get("NEXUS_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("NEXUS_API_KEY is required for a Nexus upload.")

    manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    version = manifest["version"]
    files_response = get_json(f"/mods/{MOD_ID}/files", api_key)
    existing_files = files_response.get("data", {}).get("mod_files")
    if not isinstance(existing_files, list):
        raise SystemExit("Nexus API did not return the mod file list.")

    upload_matrix = []
    for expected in manifest["nexus_files"]:
        matches = [
            item
            for item in existing_files
            if item.get("name") == expected["display_name"]
        ]
        if len(matches) != 1:
            raise SystemExit(
                f"Expected exactly one existing Nexus file named {expected['display_name']!r}; "
                f"found {len(matches)}. No files were uploaded."
            )

        file_id = str(matches[0].get("id", ""))
        if not file_id.isdigit():
            raise SystemExit(
                f"Nexus returned an invalid file ID for {expected['display_name']!r}."
            )

        versions_response = get_json(
            f"/mod-files/{quote(file_id, safe='')}/versions", api_key
        )
        versions = versions_response.get("data", {}).get("versions")
        if not isinstance(versions, list) or not versions:
            raise SystemExit(
                f"Nexus returned no versions for {expected['display_name']!r}."
            )

        already_uploaded = [
            item for item in versions if str(item.get("version")) == version
        ]
        if already_uploaded:
            if any(
                item.get("category") != expected["category"]
                for item in already_uploaded
            ):
                raise SystemExit(
                    f"The existing {expected['display_name']!r} version {version} has an unexpected "
                    "Nexus category. No files were uploaded."
                )
            continue

        latest = max(versions, key=lambda item: int(item.get("position", -1)))
        if latest.get("category") != expected["category"]:
            raise SystemExit(
                f"The existing {expected['display_name']!r} file is categorized as "
                f"{latest.get('category')!r}, expected {expected['category']!r}. No files were uploaded."
            )

        upload_matrix.append(
            {
                "file_id": file_id,
                **expected,
            }
        )

    output = Path(os.environ["GITHUB_OUTPUT"])
    output.write_text(
        "matrix="
        + json.dumps(upload_matrix, separators=(",", ":"))
        + "\n"
        + f"has_uploads={'true' if upload_matrix else 'false'}\n",
        encoding="utf-8",
    )
    print(f"Resolved {len(upload_matrix)} Nexus file(s) that need version {version}.")


if __name__ == "__main__":
    main()
