#!/usr/bin/env python3
"""Aggregate PS5 payload catalogue into payloads.json.

Reads `sources.json` (curated upstream repo list), enriches it with the live
`phantomptr/ps5upload` CATALOGUE when possible, queries each upstream repo's
latest release, picks the canonical asset, and writes `payloads.json` in the
ps5-payload-manager custom-repository schema.

Behaviour notes:
- No binaries are downloaded. Checksums come from the GitHub Release API
  `digest` field (sha256:...). Forgejo/Gitea and missing-digest assets get an
  empty checksum string.
- `/releases/latest` is tried first; if it 404s (pre-release-only repo) we fall
  back to the first element of `/releases`.
- `name` key is emitted before `payloads` per the ps5-payload-manager spec.
"""

import json
import re
import subprocess
import urllib.request
from pathlib import Path

SOURCES_FILE = "sources.json"
OUTPUT_FILE = "payloads.json"
README_FILE = "README.md"
PS5UPLOAD_CATALOGUE_URL = (
    "https://raw.githubusercontent.com/phantomptr/ps5upload/main/"
    "client/src-tauri/src/commands/payloads.rs"
)
CATALOGUE_NAME = "PS5 Payload Catalogue"


# ─── HTTP helpers ──────────────────────────────────────────────────────
def http_get(url: str, headers: dict | None = None, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "ps5-payload-catalogue/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8")


def gh_api(endpoint: str) -> dict | list | None:
    """GitHub API via gh CLI (handles GITHUB_TOKEN auth in CI)."""
    try:
        result = subprocess.run(
            ["gh", "api", endpoint], capture_output=True, text=True, check=True
        )
        return json.loads(result.stdout) if result.stdout.strip() else None
    except Exception as e:
        print(f"  gh api {endpoint} failed: {e}")
        return None


def forgejo_api(host: str, endpoint: str) -> dict | list | None:
    try:
        url = f"https://{host}/api/v1/{endpoint}"
        return json.loads(http_get(url, timeout=30))
    except Exception as e:
        print(f"  forgejo {url} failed: {e}")
        return None


def get_latest_release(host: str, owner: str, repo: str) -> dict | None:
    """Fetch /releases/latest with pre-release fallback."""
    if host == "github.com":
        release = gh_api(f"repos/{owner}/{repo}/releases/latest")
        if release:
            return release
        releases = gh_api(f"repos/{owner}/{repo}/releases?per_page=1") or []
        return releases[0] if releases else None
    else:
        release = forgejo_api(host, f"repos/{owner}/{repo}/releases/latest")
        if release and isinstance(release, dict):
            return release
        releases = forgejo_api(host, f"repos/{owner}/{repo}/releases?limit=1") or []
        return releases[0] if releases else None


# ─── Asset selection ──────────────────────────────────────────────────
def score_asset(name: str, asset_pattern: str, has_extract: bool, preferred_ext: str) -> float:
    name_lower = name.lower()
    if has_extract and name.endswith(".zip"):
        return 20
    if not (name.endswith(".elf") or name.endswith(".bin") or (has_extract and name.endswith(".zip"))):
        if not name.endswith(preferred_ext):
            return -1
    if asset_pattern and not re.search(asset_pattern, name, re.IGNORECASE):
        return -1
    score = 0.0
    if name.endswith(preferred_ext):
        score += 5
    if "ps5" in name_lower:
        score += 10
    if "ps4" in name_lower:
        score -= 10
    if "install" in name_lower:
        score -= 5
    score -= len(name) / 100.0
    return score


def pick_asset(assets: list, asset_pattern: str, has_extract: bool, preferred_ext: str) -> dict | None:
    selected = None
    best = -2.0
    for asset in assets:
        s = score_asset(asset["name"], asset_pattern, has_extract, preferred_ext)
        if s > best:
            best = s
            selected = asset
    return selected if best > -1 else None


def get_checksum(asset: dict, host: str) -> str:
    if host == "github.com":
        digest = asset.get("digest") or ""
        if digest.startswith("sha256:"):
            return digest.split(":", 1)[1]
    return ""


# ─── Category derivation ──────────────────────────────────────────────
CATEGORY_RULES = [
    (r"kernel|kstuff|exploit|patch|jb|jailbreak", "Kernel"),
    (r"\bftp\b|file transfer", "File Transfer"),
    (r"\bhttp\b|web|telnet|\bdns\b", "Networking"),
    (r"save", "Save Manager"),
    (r"debug|gdb", "Debugger"),
    (r"linux|loader|launch|homebrew|mount|backup|pkg", "Launcher"),
    (r"cheat", "Misc"),
    (r"controller|input|ghostpad|virtual pad", "Misc"),
    (r"log|klog", "Networking"),
]


def derive_category(name: str, description: str) -> str:
    text = f"{name} {description}".lower()
    for pattern, category in CATEGORY_RULES:
        if re.search(pattern, text):
            return category
    return "Misc"


# ─── ps5upload catalogue enrichment ──────────────────────────────────
def strip_block_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def extract_catalogue_block(text: str) -> str:
    marker = "const CATALOGUE: &[CatalogueEntry] = &["
    start = text.find(marker)
    if start == -1:
        return ""
    start += len(marker)
    struct_depth = 0
    array_depth = 0
    in_str = False
    escape = False
    for i, ch in enumerate(text[start:], start):
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                struct_depth += 1
            elif ch == "}":
                struct_depth -= 1
            elif ch == "[":
                if struct_depth == 0:
                    array_depth += 1
            elif ch == "]":
                if struct_depth == 0:
                    if array_depth == 0:
                        return text[start:i]
                    array_depth -= 1
    return ""


def split_entries(block: str) -> list[str]:
    entries = []
    for m in re.finditer(r"CatalogueEntry\s*\{", block):
        s = m.start()
        depth = 0
        in_str = False
        escape = False
        for i, ch in enumerate(block[s:], s):
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        entries.append(block[s : i + 1])
                        break
    return entries


def parse_str(entry: str, key: str) -> str | None:
    m = re.search(rf"\b{re.escape(key)}\s*:\s*\"([^\"]*)\"", entry)
    return m.group(1) if m else None


def fetch_ps5upload_enrichment() -> dict:
    """Return {(host, owner, repo): {display_name, description}} from ps5upload."""
    try:
        raw = strip_block_comments(http_get(PS5UPLOAD_CATALOGUE_URL, timeout=30))
    except Exception as e:
        print(f"ps5upload catalogue fetch failed (continuing without enrichment): {e}")
        return {}
    block = extract_catalogue_block(raw)
    if not block:
        print("ps5upload CATALOGUE block not found; skipping enrichment")
        return {}
    enrichment = {}
    for entry_text in split_entries(block):
        host = parse_str(entry_text, "repo_host")
        owner = parse_str(entry_text, "repo_owner")
        repo = parse_str(entry_text, "repo_name")
        if not (host and owner and repo):
            continue
        display_name = parse_str(entry_text, "display_name")
        description = parse_str(entry_text, "description")
        enrichment[(host, owner.lower(), repo.lower())] = {
            "display_name": display_name,
            "description": description,
        }
    print(f"ps5upload enrichment loaded: {len(enrichment)} entries")
    return enrichment


# ─── Main aggregation ────────────────────────────────────────────────
def build_payload_entry(src: dict, enrichment: dict) -> dict | None:
    host = src["host"]
    owner = src["owner"]
    repo = src["repo"]
    key = (host, owner.lower(), repo.lower())
    enrich = enrichment.get(key, {})

    display_name = enrich.get("display_name") or src.get("display_name") or repo
    description = enrich.get("description") or src.get("description") or ""
    asset_pattern = src.get("asset_pattern", "")
    has_extract = bool(src.get("extract_file"))
    preferred_ext = ".bin" if repo.lower() == "etahen" else ".elf"

    print(f"Checking {owner}/{repo} on {host}...")
    release = get_latest_release(host, owner, repo)
    if not release:
        print("  no release found, skipping")
        return None

    assets = release.get("assets", [])
    if not assets:
        print(f"  no assets in release {release.get('tag_name')}, skipping")
        return None

    selected = pick_asset(assets, asset_pattern, has_extract, preferred_ext)
    if not selected:
        print(f"  no suitable asset for {owner}/{repo}, skipping")
        return None

    version = release.get("tag_name", "")
    last_update = (release.get("published_at") or "")[:10]
    checksum = get_checksum(selected, host)
    category = derive_category(display_name, description)
    source_url = f"https://{host}/{owner}/{repo}/releases"

    print(f"  → {selected['name']} @ {version} ({category})")
    return {
        "name": display_name,
        "filename": selected["name"],
        "url": selected["browser_download_url"],
        "description": description,
        "version": version,
        "category": category,
        "checksum": checksum,
        "last_update": last_update,
        "source": source_url,
    }


def update_readme(payloads: list[dict]) -> None:
    rows = [
        "| Name | Version | Category | Description | Last Updated | Source |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for p in payloads:
        name = p.get("name", "")
        version = p.get("version", "")
        category = p.get("category", "")
        description = (p.get("description") or "No description provided.").replace("|", "\\|")
        last_update = p.get("last_update", "")
        source = p.get("source", "")
        rows.append(
            f"| **{name}** | `{version}` | {category} | {description} | `{last_update}` | [Source]({source}) |"
        )
    table = "\n".join(rows)

    start = "<!-- PAYLOADS_START -->"
    end = "<!-- PAYLOADS_END -->"

    if not Path(README_FILE).exists():
        return
    with open(README_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    if start in content and end in content:
        pattern = re.compile(f"{re.escape(start)}.*?{re.escape(end)}", re.DOTALL)
        content = pattern.sub(f"{start}\n{table}\n{end}", content)
        with open(README_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {README_FILE}")


def main() -> None:
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        sources = json.load(f)
    print(f"Loaded {len(sources)} sources from {SOURCES_FILE}")

    enrichment = fetch_ps5upload_enrichment()

    payloads = []
    skipped = []
    for src in sources:
        item = build_payload_entry(src, enrichment)
        if item:
            payloads.append(item)
        else:
            skipped.append(f"{src['owner']}/{src['repo']}")

    document = {"name": CATALOGUE_NAME, "payloads": payloads}
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(document, f, indent=2, ensure_ascii=False)
    print(f"Wrote {OUTPUT_FILE} ({len(payloads)} payloads, {len(skipped)} skipped)")
    if skipped:
        print(f"Skipped: {', '.join(skipped)}")

    update_readme(payloads)


if __name__ == "__main__":
    main()
