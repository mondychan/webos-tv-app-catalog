#!/usr/bin/env python3
"""Build Glasshouse repo.json from the latest stable GitHub releases.

Only release assets that match an explicitly configured webOS IPK pattern are
published. The asset's GitHub SHA-256 digest is used when available; otherwise
we download the asset once and calculate SHA-256 locally. The output is written
atomically, so an upstream/API error never destroys the last working catalogue.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "catalog-sources.json"
OUTPUT = ROOT / "repo.json"
USER_AGENT = "glasshouse-webos-catalog-updater/1.0"


def request(url: str, token: str | None = None, accept: str = "application/vnd.github+json") -> urllib.request.Response:
    headers = {
        "Accept": accept,
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        return urllib.request.urlopen(req, timeout=90)
    except urllib.error.HTTPError as exc:
        body = exc.read(1000).decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {exc.code} for {url}: {body}") from exc
    except Exception as exc:
        raise RuntimeError(f"Request failed for {url}: {exc}") from exc


def get_json(url: str, token: str | None) -> dict[str, Any]:
    with request(url, token) as response:
        return json.loads(response.read().decode("utf-8"))


def asset_sha256(asset: dict[str, Any], token: str | None) -> str:
    digest = asset.get("digest") or ""
    if isinstance(digest, str) and re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
        return digest.split(":", 1)[1].lower()

    # GitHub's release-assets API did not always populate `digest`. Fall back
    # to downloading only that asset rather than publishing an unhashed IPK.
    url = asset.get("browser_download_url")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise RuntimeError(f"Asset {asset.get('name')} has no usable download URL or SHA-256")
    hasher = hashlib.sha256()
    with request(url, token, accept="application/octet-stream") as response:
        while chunk := response.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def build_package(spec: dict[str, Any], token: str | None) -> dict[str, Any]:
    repository = spec["repository"]
    release = get_json(f"https://api.github.com/repos/{repository}/releases/latest", token)
    if release.get("draft") or release.get("prerelease"):
        raise RuntimeError(f"{repository}: latest endpoint returned a draft/prerelease")

    pattern = re.compile(spec["assetPattern"])
    matches: list[tuple[dict[str, Any], re.Match[str]]] = []
    for asset in release.get("assets", []):
        match = pattern.fullmatch(str(asset.get("name", "")))
        if match:
            matches.append((asset, match))

    if len(matches) != 1:
        found = [a.get("name") for a, _ in matches]
        raise RuntimeError(
            f"{repository}: expected exactly one matching webOS IPK asset, found {len(matches)}: {found}"
        )

    asset, match = matches[0]
    version = match.group("version")
    download_url = asset.get("browser_download_url")
    if not isinstance(download_url, str) or not download_url.startswith("https://"):
        raise RuntimeError(f"{repository}: IPK asset has no HTTPS download URL")
    digest = asset_sha256(asset, token)
    size = asset.get("size")
    if not isinstance(size, int) or size <= 0:
        size = None

    manifest = {
        "id": spec["id"],
        "version": version,
        "type": spec["type"],
        "title": spec["title"],
        "appDescription": spec["description"],
        "iconUri": spec["iconUri"],
        "sourceUrl": f"https://github.com/{repository}",
        "rootRequired": bool(spec.get("rootRequired", False)),
        "ipkUrl": download_url,
        "ipkHash": {"sha256": digest},
    }
    if size:
        manifest["ipkSize"] = size

    package: dict[str, Any] = {
        "id": spec["id"],
        "title": spec["title"],
        "shortDescription": spec["description"],
        "iconUri": spec["iconUri"],
        "manifest": manifest,
    }

    return {
        "package": package,
        "version": version,
        "release": release.get("html_url", ""),
        "asset": asset.get("name", ""),
    }


def main() -> int:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    results = [build_package(spec, token) for spec in config["apps"]]
    packages = [result["package"] for result in results]

    ids = [package["id"] for package in packages]
    if len(ids) != len(set(ids)):
        raise RuntimeError("Duplicate app IDs in catalogue configuration")

    catalogue = {
        "paging": {
            "page": 1,
            "count": len(packages),
            "maxPage": 1,
            "itemsTotal": len(packages),
        },
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "packages": packages,
    }

    rendered = json.dumps(catalogue, ensure_ascii=False, indent=2) + "\n"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=OUTPUT.parent, delete=False) as tmp:
        tmp.write(rendered)
        temp_name = tmp.name
    os.replace(temp_name, OUTPUT)

    print(f"Generated {OUTPUT.name}: {len(packages)} packages")
    for result in results:
        print(f"  {result['package']['id']} {result['version']} <- {result['asset']} ({result['release']})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
