#!/usr/bin/env python3
"""Verify newly uploaded Nexus versions against their pre-upload settings."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote

from resolve_nexus_files import (
    API_V3_BASE,
    MOD_ID,
    get_json,
    read_version_metadata,
    version_position,
)


METADATA_KEYS = (
    "description",
    "primary_mod_manager_download",
    "allow_mod_manager_download",
    "show_requirements_pop_up",
)


def require_object_list(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise SystemExit(f"{label} must be a JSON list of objects.")
    return cast(list[dict[str, Any]], value)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: verify_nexus_uploads.py RELEASE_ASSET_MANIFEST")

    api_key = os.environ.get("NEXUS_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("NEXUS_API_KEY is required for Nexus upload verification.")

    raw_uploads = os.environ.get("EXPECTED_NEXUS_UPLOADS_JSON", "").strip()
    if not raw_uploads:
        raise SystemExit("EXPECTED_NEXUS_UPLOADS_JSON is required.")
    try:
        expected_uploads = require_object_list(
            json.loads(raw_uploads), "EXPECTED_NEXUS_UPLOADS_JSON"
        )
    except json.JSONDecodeError as error:
        raise SystemExit("EXPECTED_NEXUS_UPLOADS_JSON is invalid JSON.") from error
    if not expected_uploads:
        raise SystemExit("Expected at least one newly uploaded Nexus file.")

    manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    version = str(manifest["version"])
    manifest_files = require_object_list(manifest.get("nexus_files"), "nexus_files")
    manifest_by_name = {item.get("display_name"): item for item in manifest_files}
    if len(manifest_by_name) != len(manifest_files):
        raise SystemExit("Release manifest contains duplicate Nexus display names.")

    files_response = get_json(API_V3_BASE, f"/mods/{MOD_ID}/files", api_key)
    existing_files = require_object_list(
        files_response.get("data", {}).get("mod_files"), "Nexus mod file list"
    )

    for expected in expected_uploads:
        display_name = expected.get("display_name")
        manifest_entry = manifest_by_name.get(display_name)
        if manifest_entry is None:
            raise SystemExit(
                f"Uploaded Nexus file {display_name!r} is absent from the manifest."
            )
        for key in ("archive", "category", "update_mod_version"):
            if expected.get(key) != manifest_entry.get(key):
                raise SystemExit(
                    f"Uploaded Nexus file {display_name!r} does not match the manifest "
                    f"field {key!r}."
                )

        matches = [item for item in existing_files if item.get("name") == display_name]
        if len(matches) != 1:
            raise SystemExit(
                f"Expected exactly one Nexus file named {display_name!r}; "
                f"found {len(matches)}."
            )
        file_id = str(matches[0].get("id", ""))
        if file_id != str(expected.get("file_id", "")) or not file_id.isdigit():
            raise SystemExit(f"Nexus file ID changed for {display_name!r}.")

        versions_response = get_json(
            API_V3_BASE, f"/mod-files/{quote(file_id, safe='')}/versions", api_key
        )
        versions = require_object_list(
            versions_response.get("data", {}).get("versions"),
            f"Nexus versions for {display_name!r}",
        )
        uploaded = [item for item in versions if str(item.get("version")) == version]
        if len(uploaded) != 1:
            raise SystemExit(
                f"Expected exactly one Nexus version {version!r} for {display_name!r}; "
                f"found {len(uploaded)}."
            )
        latest = max(
            versions, key=lambda item: version_position(item, str(display_name))
        )
        if uploaded[0].get("id") != latest.get("id"):
            raise SystemExit(
                f"Nexus version {version!r} is not newest for {display_name!r}."
            )

        actual_metadata = read_version_metadata(latest, expected, api_key)
        changed_fields = [
            key
            for key in METADATA_KEYS
            if actual_metadata.get(key) != expected.get(key)
        ]
        if changed_fields:
            raise SystemExit(
                f"Nexus changed uploaded metadata for {display_name!r}: "
                f"{', '.join(changed_fields)}."
            )

    print(
        f"Verified {len(expected_uploads)} Nexus upload(s) for version {version} "
        "against their pre-upload metadata."
    )


if __name__ == "__main__":
    main()
