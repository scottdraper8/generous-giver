#!/usr/bin/env python3
"""Resolve existing Nexus file entries and avoid duplicate version uploads."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote


API_V3_BASE = "https://api.nexusmods.com/v3"
API_V1_BASE = "https://api.nexusmods.com/v1"
GRAPHQL_URL = "https://api.nexusmods.com/v2/graphql"
MOD_ID = "7017976566438"
GAME_DOMAIN = "nomanssky"
GAME_SCOPED_MOD_ID = "4774"


def get_json(base_url: str, path: str, api_key: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{base_url}{path}",
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


def post_json(url: str, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Generous-Giver release workflow",
            "apikey": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return cast(dict[str, Any], json.load(response))
    except urllib.error.HTTPError as error:
        raise SystemExit(
            f"Nexus API request failed with HTTP {error.code}: {url}"
        ) from None
    except urllib.error.URLError as error:
        raise SystemExit(f"Nexus API request failed: {error.reason}") from None


def get_file_settings(file_uid: str, api_key: str) -> dict[str, Any]:
    response = post_json(
        GRAPHQL_URL,
        {
            "query": """
                query CurrentFileSettings($uids: [ID!]!) {
                  modFilesByUid(uids: $uids) {
                    nodes {
                      fileId
                      name
                      description
                      manager
                      primary
                      requirementsAlert
                    }
                  }
                }
            """,
            "variables": {"uids": [file_uid]},
        },
        api_key,
    )
    errors = response.get("errors")
    if errors:
        messages = []
        if isinstance(errors, list):
            for error in errors:
                if isinstance(error, dict) and isinstance(error.get("message"), str):
                    message = " ".join(error["message"].split())[:500]
                    if message:
                        messages.append(message)
        detail = "; ".join(messages) or "Unknown GraphQL error"
        raise SystemExit(
            f"Nexus GraphQL returned errors: {detail}. No files were uploaded."
        )
    nodes = response.get("data", {}).get("modFilesByUid", {}).get("nodes")
    if not isinstance(nodes, list) or len(nodes) != 1 or not isinstance(nodes[0], dict):
        raise SystemExit(
            "Nexus did not return exactly one current file-settings record. "
            "No files were uploaded."
        )
    return cast(dict[str, Any], nodes[0])


def read_boolean_setting(settings: dict[str, Any], key: str, display_name: str) -> bool:
    value = settings.get(key)
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    raise SystemExit(
        f"Nexus returned an invalid {key!r} setting for {display_name!r}. "
        "No files were uploaded."
    )


def version_position(version: dict[str, Any], display_name: str) -> Decimal:
    try:
        position = Decimal(str(version["position"]))
    except (InvalidOperation, KeyError, TypeError, ValueError):
        raise SystemExit(
            f"Nexus returned an invalid version position for {display_name!r}. "
            "No files were uploaded."
        ) from None
    if not position.is_finite():
        raise SystemExit(
            f"Nexus returned an invalid version position for {display_name!r}. "
            "No files were uploaded."
        )
    return position


def read_version_metadata(
    version: dict[str, Any], expected: dict[str, Any], api_key: str
) -> dict[str, Any]:
    display_name = expected["display_name"]
    if version.get("name") != display_name:
        raise SystemExit(
            f"Nexus reports a version in file {display_name!r} as "
            f"{version.get('name')!r}. No files were uploaded."
        )
    if version.get("category") != expected["category"]:
        raise SystemExit(
            f"Nexus reports version {version.get('version')!r} at position "
            f"{version.get('position')!r} in file {display_name!r} as category "
            f"{version.get('category')!r}, expected {expected['category']!r}. "
            "No files were uploaded."
        )

    game_scoped_file_id = str(version.get("game_scoped_id", ""))
    if not game_scoped_file_id.isdigit():
        raise SystemExit(
            f"Nexus returned an invalid version ID for {display_name!r}. "
            "No files were uploaded."
        )
    current_file = get_json(
        API_V1_BASE,
        f"/games/{GAME_DOMAIN}/mods/{GAME_SCOPED_MOD_ID}/files/"
        f"{quote(game_scoped_file_id, safe='')}.json",
        api_key,
    )
    if str(current_file.get("file_id", "")) != game_scoped_file_id:
        raise SystemExit(
            f"Nexus v1 and v3 disagree on a version ID for {display_name!r}. "
            "No files were uploaded."
        )
    if current_file.get("name") != display_name:
        raise SystemExit(
            f"Nexus v1 reports the file name as {current_file.get('name')!r}, "
            f"expected {display_name!r}. No files were uploaded."
        )
    if str(current_file.get("version")) != str(version.get("version")):
        raise SystemExit(
            f"Nexus v1 and v3 disagree on a file version for {display_name!r}. "
            "No files were uploaded."
        )

    file_uid = str(current_file.get("uid", ""))
    if not file_uid.isdigit():
        raise SystemExit(
            f"Nexus returned an invalid file UID for {display_name!r}. "
            "No files were uploaded."
        )
    settings = get_file_settings(file_uid, api_key)
    if str(settings.get("fileId", "")) != game_scoped_file_id:
        raise SystemExit(
            f"Nexus file metadata does not match the version ID for {display_name!r}. "
            "No files were uploaded."
        )
    if settings.get("name") != display_name:
        raise SystemExit(
            f"Nexus file metadata reports the name as {settings.get('name')!r}, "
            f"expected {display_name!r}. No files were uploaded."
        )
    description = settings.get("description")
    if not isinstance(description, str) or not description.strip():
        raise SystemExit(
            f"Nexus did not return a non-empty description for {display_name!r}. "
            "No files were uploaded."
        )
    is_primary = read_boolean_setting(settings, "primary", display_name)
    if current_file.get("is_primary") != is_primary:
        raise SystemExit(
            f"Nexus API responses disagree on the primary-download setting for "
            f"{display_name!r}. No files were uploaded."
        )
    if "is_primary" in version and version["is_primary"] != is_primary:
        raise SystemExit(
            f"Nexus API responses disagree on the primary-download setting for "
            f"{display_name!r}. No files were uploaded."
        )

    return {
        "description": description,
        "primary_mod_manager_download": is_primary,
        "allow_mod_manager_download": read_boolean_setting(
            settings, "manager", display_name
        ),
        "show_requirements_pop_up": read_boolean_setting(
            settings, "requirementsAlert", display_name
        ),
    }


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: resolve_nexus_files.py RELEASE_ASSET_MANIFEST")

    api_key = os.environ.get("NEXUS_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("NEXUS_API_KEY is required for a Nexus upload.")

    manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    version = manifest["version"]
    files_response = get_json(API_V3_BASE, f"/mods/{MOD_ID}/files", api_key)
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
            API_V3_BASE, f"/mod-files/{quote(file_id, safe='')}/versions", api_key
        )
        versions = versions_response.get("data", {}).get("versions")
        if not isinstance(versions, list) or not versions:
            raise SystemExit(
                f"Nexus returned no versions for {expected['display_name']!r}."
            )

        already_uploaded = [
            item for item in versions if str(item.get("version")) == version
        ]
        if len(already_uploaded) > 1:
            raise SystemExit(
                f"Nexus returned multiple {expected['display_name']!r} versions named "
                f"{version!r}. No files were uploaded."
            )
        latest = max(
            versions,
            key=lambda item: version_position(item, expected["display_name"]),
        )
        if already_uploaded:
            uploaded = already_uploaded[0]
            print(
                f"Found Nexus version {version!r} for {expected['display_name']!r} "
                f"at position {uploaded.get('position')!r} with category "
                f"{uploaded.get('category')!r}; newest reported version is "
                f"{latest.get('version')!r} at position {latest.get('position')!r} "
                f"with category {latest.get('category')!r}."
            )
        latest_metadata = read_version_metadata(latest, expected, api_key)
        if already_uploaded:
            if uploaded.get("id") != latest.get("id"):
                raise SystemExit(
                    f"Nexus version {version!r} is not the newest version of "
                    f"{expected['display_name']!r}. No files were uploaded."
                )
            uploaded_position = version_position(uploaded, expected["display_name"])
            predecessors = [
                item
                for item in versions
                if version_position(item, expected["display_name"]) < uploaded_position
            ]
            if not predecessors:
                raise SystemExit(
                    f"Nexus has no preceding version from which to verify metadata for "
                    f"{expected['display_name']!r}. No files were uploaded."
                )
            predecessor = max(
                predecessors,
                key=lambda item: version_position(item, expected["display_name"]),
            )
            predecessor_metadata = read_version_metadata(predecessor, expected, api_key)
            if latest_metadata != predecessor_metadata:
                raise SystemExit(
                    f"Nexus version {version!r} changed file metadata for "
                    f"{expected['display_name']!r}. No files were uploaded."
                )
            continue

        upload_matrix.append(
            {
                "file_id": file_id,
                **latest_metadata,
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
