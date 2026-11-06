#!/usr/bin/env python3
"""Refresh the public Nexus Mods download badge without using an API key."""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path


API_URL = "https://api.nexusmods.com/v3/games/nomanssky/mods/4774"
BADGE_PATH = Path(__file__).resolve().parents[1] / "assets/badges/nexus-downloads.svg"
ICON_PATTERN = re.compile(
    r'<image x="5" y="3" width="14" height="14" href="(?P<icon>data:image/svg\+xml;base64,[^"]+)"/>'
)


def fetch_download_count() -> int:
    request = urllib.request.Request(
        API_URL,
        headers={"Accept": "application/json", "User-Agent": "Generous-Giver badge updater"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)

    downloads = payload.get("data", {}).get("stats", {}).get("downloads")
    if isinstance(downloads, bool) or not isinstance(downloads, int) or downloads < 0:
        raise SystemExit("Nexus Mods returned an invalid total-download count.")
    return downloads


def render_badge(downloads: int, current_svg: str) -> str:
    icon_match = ICON_PATTERN.search(current_svg)
    if icon_match is None:
        raise SystemExit("Could not locate the Nexus icon in the existing badge SVG.")

    value = str(downloads)
    value_width = max(17, 7 * len(value) + 10)
    total_width = 94 + value_width
    value_center = (94 + value_width / 2) * 10
    value_text_length = len(value) * 70
    icon = icon_match.group("icon")

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="20" role="img" aria-label="Nexus Mods: {value}"><title>Nexus Mods: {value}</title><filter id="blur"><feGaussianBlur stdDeviation="16"/></filter><linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient><clipPath id="r"><rect width="{total_width}" height="20" rx="3"/></clipPath><g clip-path="url(#r)"><rect width="94" height="20" fill="#6272a4"/><rect x="94" width="{value_width}" height="20" fill="#ff79c6"/><rect width="{total_width}" height="20" fill="url(#s)"/></g><g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="110"><image x="5" y="3" width="14" height="14" href="{icon}"/><g transform="scale(.1)"><g aria-hidden="true" fill="#010101"><text x="565" y="150" fill-opacity=".8" filter="url(#blur)" textLength="670">Nexus Mods</text><text x="565" y="150" fill-opacity=".3" textLength="670">Nexus Mods</text></g><text x="565" y="140" textLength="670">Nexus Mods</text></g><g transform="scale(.1)"><g aria-hidden="true" fill="#010101"><text x="{value_center:.0f}" y="150" fill-opacity=".8" filter="url(#blur)" textLength="{value_text_length}">{value}</text><text x="{value_center:.0f}" y="150" fill-opacity=".3" textLength="{value_text_length}">{value}</text></g><text x="{value_center:.0f}" y="140" textLength="{value_text_length}">{value}</text></g></g></svg>\n'''


def main() -> None:
    downloads = fetch_download_count()
    current_svg = BADGE_PATH.read_text(encoding="utf-8")
    updated_svg = render_badge(downloads, current_svg)
    if updated_svg != current_svg:
        BADGE_PATH.write_text(updated_svg, encoding="utf-8")
        print(f"Updated Nexus Mods download badge to {downloads} downloads.")
    else:
        print(f"Nexus Mods download badge already shows {downloads} downloads.")


if __name__ == "__main__":
    main()
