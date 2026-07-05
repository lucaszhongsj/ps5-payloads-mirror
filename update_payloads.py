#!/usr/bin/env python3
"""Aggregate PS5 payload catalogue into payloads.json.

Three-layer composition, all read-only against upstream:
  1. Discovery: `itsPLK/ps5-payloads-mirror/payloads.json` and
     `phantomptr/ps5upload` CATALOGUE both supply upstream repo URLs.
  2. Curation: `sources.json` overrides display name / description / asset
     selection per repo, and can `"exclude": true` to suppress one.
  3. Enrichment: `phantomptr/ps5upload` CATALOGUE provides longer
     descriptions / display names where available.

Design rules:
- A repo is identified by its full HTML URL string (e.g.
  `https://github.com/owner/repo`). All maps are keyed by the lowercased URL.
- The API response is the source of truth. Nothing is reassembled from
  parsed fragments — `version`, `published_at`, asset `name` /
  `browser_download_url` / `digest`, and the canonical repo URL (via
  `release.html_url`) all come straight from the JSON the API returns.
- No binaries are downloaded. GitHub checksums come from the asset `digest`
  field. Forgejo / missing-digest assets get an empty checksum.
- `/releases/latest` 404 → fall back to `/releases[0]` for pre-release-only
  repos.
"""

import json
import re
import subprocess
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

SOURCES_FILE = "sources.json"
OUTPUT_FILE = "payloads.json"
README_FILE = "README.md"
ITSPLK_DISCOVERY_URL = (
    "https://raw.githubusercontent.com/itsPLK/ps5-payloads-mirror/main/payloads.json"
)
PS5UPLOAD_CATALOGUE_URL = (
    "https://raw.githubusercontent.com/phantomptr/ps5upload/main/"
    "client/src-tauri/src/commands/payloads.rs"
)
CATALOGUE_NAME = "lucaszhongsj/ps5-payloads-atlas"
CST = timezone(timedelta(hours=8))  # UTC+8 / 东八区


# ─── URL helpers ─────────────────────────────────────────────────────
def normalize_repo_url(url: str) -> str:
    """Lowercase a repo HTML URL for use as a map key. Trims trailing slash and .git."""
    if not url:
        return ""
    url = url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    return url.lower()


def parse_repo_url(url: str):
    """Extract (host, owner, repo) from a repo HTML URL for API calls."""
    m = re.search(r"https?://([^/]+)/([^/]+)/([^/?#]+)", url or "")
    if not m:
        return None
    host, owner, repo = m.groups()
    repo = repo.rstrip("/")
    if repo.endswith(".git"):
        repo = repo[:-4]
    return host, owner, repo


def format_last_update(iso_str: str) -> str:
    """ISO 8601 UTC → 'YYYY-MM-DD HH:MM:SS UTC+8'."""
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.astimezone(CST).strftime("%Y-%m-%d %H:%M:%S UTC+8")
    except (ValueError, TypeError):
        return iso_str


# ─── HTTP / API ──────────────────────────────────────────────────────
def http_get(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "ps5-payloads-atlas/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8")


def gh_api(endpoint: str):
    try:
        result = subprocess.run(
            ["gh", "api", endpoint], capture_output=True, text=True, check=True
        )
        return json.loads(result.stdout) if result.stdout.strip() else None
    except Exception as e:
        print(f"  gh api {endpoint} failed: {e}")
        return None


def forgejo_api(host: str, endpoint: str):
    try:
        return json.loads(http_get(f"https://{host}/api/v1/{endpoint}"))
    except Exception as e:
        print(f"  forgejo {host}/{endpoint} failed: {e}")
        return None


def get_latest_release(repo_url: str) -> dict | None:
    """Fetch latest release (with pre-release fallback) for a repo URL."""
    info = parse_repo_url(repo_url)
    if not info:
        return None
    host, owner, repo = info
    if host == "github.com":
        release = gh_api(f"repos/{owner}/{repo}/releases/latest")
        if release:
            return release
        releases = gh_api(f"repos/{owner}/{repo}/releases?per_page=1") or []
        return releases[0] if releases else None
    release = forgejo_api(host, f"repos/{owner}/{repo}/releases/latest")
    if release and isinstance(release, dict):
        return release
    releases = forgejo_api(host, f"repos/{owner}/{repo}/releases?limit=1") or []
    return releases[0] if releases else None


def repo_url_from_release(release: dict) -> str:
    """`https://github.com/o/r/releases/tag/v1` → `https://github.com/o/r` (lowercased).

    Matches the full `/releases/tag/` anchor so owners/repos whose names contain
    'releases' (e.g. `releases-app/foo`) are not mis-truncated.
    """
    html_url = release.get("html_url") or ""
    m = re.search(r"^(.*?)/releases/tag/", html_url)
    return m.group(1).lower() if m else ""


# ─── Asset selection ─────────────────────────────────────────────────
def pick_asset(assets: list, asset_pattern: str, repo_url: str) -> dict | None:
    """Select the canonical payload asset by explicit priority (no magic numbers).

    Keep only .elf/.bin → if asset_pattern given, narrow to matches (with a
    warning + fallback to unfiltered if the pattern matches nothing) → prefer
    .elf over .bin, non-ps4 over ps4, shorter filename over longer.
    """
    candidates = [a for a in assets if a["name"].endswith((".elf", ".bin"))]
    if not candidates:
        return None
    if asset_pattern:
        matched = [a for a in candidates if re.search(asset_pattern, a["name"], re.IGNORECASE)]
        if not matched:
            print(f"  warning: asset_pattern {asset_pattern!r} matched no asset for {repo_url}; falling back")
        else:
            candidates = matched
    return min(
        candidates,
        key=lambda a: (
            "ps4" in a["name"].lower(),                # avoid ps4 builds first (PS5 catalogue)
            0 if a["name"].endswith(".elf") else 1,   # then prefer .elf over .bin
            len(a["name"]),                            # then shorter canonical name
        ),
    )


def get_checksum(asset: dict) -> str:
    """SHA-256 hex from the asset's `digest` field ('sha256:...' on GitHub; absent on Forgejo)."""
    digest = asset.get("digest") or ""
    return digest.split(":", 1)[1] if digest.startswith("sha256:") else ""


# ─── Category derivation ─────────────────────────────────────────────
CATEGORY_RULES = [
    (r"kernel|kstuff|exploit|patch|jb|jailbreak", "Kernel"),
    (r"\bftp\b|ftpsrv|file transfer", "File Transfer"),
    (r"\bhttp\b|telnet|\bdns\b|klog", "Networking"),  # `web` dropped: too generic (collides with "web-based dashboard")
    (r"save", "Save Manager"),
    (r"debug|gdb", "Debugger"),
    (r"dump", "Dumper"),
    (r"linux|loader|launch|homebrew|mount|backup|pkg", "Launcher"),
    (r"cheat", "Misc"),
    (r"controller|input|ghostpad|virtual pad", "Misc"),
]


def derive_category(name: str, description: str) -> str:
    text = f"{name} {description}".lower()
    for pattern, category in CATEGORY_RULES:
        if re.search(pattern, text):
            return category
    return "Misc"


# ─── Discovery: itsPLK payloads.json ────────────────────────────────
def fetch_itsplk_discovery() -> dict:
    """Return {repo_url_lower: {repo_url, display_name, description, asset_pattern}}."""
    try:
        data = json.loads(http_get(ITSPLK_DISCOVERY_URL, timeout=30))
    except Exception as e:
        print(f"itsPLK discovery fetch failed (continuing from sources.json only): {e}")
        return {}
    discovered = {}
    for p in data:
        repo_url = p.get("source", "")
        info = parse_repo_url(repo_url)
        if not info:
            continue
        # `source` in itsPLK points at .../releases; trim to the repo root URL.
        # Anchored regex avoids mis-truncation when owner/repo names contain
        # 'releases' (e.g. releases-app/foo/releases).
        m = re.search(r"^(.*?)/releases(?:/|$)", repo_url)
        repo_url = (m.group(1) if m else repo_url).rstrip("/")
        discovered[normalize_repo_url(repo_url)] = {
            "repo_url": repo_url,
            "display_name": p.get("name"),
            "description": p.get("description") or "",
            "asset_pattern": p.get("asset_pattern") or "",
        }
    print(f"itsPLK discovery loaded: {len(discovered)} repos")
    return discovered


# ─── Enrichment + discovery: ps5upload CATALOGUE ────────────────────
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


def split_catalogue_entries(block: str) -> list[str]:
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


def parse_catalogue_str(entry: str, key: str) -> str | None:
    """Read a Rust string literal value for `key`. Handles `\\\"` escapes so
    descriptions containing escaped quotes are not truncated."""
    m = re.search(rf'\b{re.escape(key)}\s*:\s*"((?:\\.|[^"\\])*)"', entry)
    if not m:
        return None
    raw = m.group(1)
    # Unescape the Rust escapes we are likely to see in catalogue strings.
    return raw.replace('\\"', '"').replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")


def fetch_ps5upload_catalogue() -> dict:
    """Return {repo_url_lower: {repo_url, display_name, description, asset_name_hint}}.

    ps5upload CATALOGUE is used both for discovery and for enrichment.
    """
    try:
        raw = strip_block_comments(http_get(PS5UPLOAD_CATALOGUE_URL, timeout=30))
    except Exception as e:
        print(f"ps5upload catalogue fetch failed (continuing without it): {e}")
        return {}
    block = extract_catalogue_block(raw)
    if not block:
        print("ps5upload CATALOGUE block not found; skipping")
        return {}
    catalogue = {}
    for entry_text in split_catalogue_entries(block):
        host = parse_catalogue_str(entry_text, "repo_host")
        owner = parse_catalogue_str(entry_text, "repo_owner")
        repo = parse_catalogue_str(entry_text, "repo_name")
        if not (host and owner and repo):
            continue
        repo_url = f"https://{host}/{owner}/{repo}"
        catalogue[normalize_repo_url(repo_url)] = {
            "repo_url": repo_url,
            "display_name": parse_catalogue_str(entry_text, "display_name"),
            "description": parse_catalogue_str(entry_text, "description"),
            "asset_name_hint": parse_catalogue_str(entry_text, "asset_name_hint") or "",
        }
    print(f"ps5upload catalogue loaded: {len(catalogue)} entries")
    return catalogue


# ─── Item builder ────────────────────────────────────────────────────
def build_item(repo_url: str, override: dict, asset_hint: str) -> tuple[dict, str] | None:
    """Fetch release, pick asset, emit schema item. Returns (item, canon_url) or None."""
    if not parse_repo_url(repo_url):
        return None
    asset_pattern = override.get("asset_pattern") or asset_hint or ""

    print(f"Checking {repo_url}...")
    release = get_latest_release(repo_url)
    if not release:
        print("  no release found, skipping")
        return None

    assets = release.get("assets", [])
    if not assets:
        print(f"  no assets in release {release.get('tag_name')}, skipping")
        return None

    selected = pick_asset(assets, asset_pattern, repo_url)
    if not selected:
        print("  no suitable asset, skipping")
        return None

    display_name = override.get("display_name") or repo_url.rstrip("/").split("/")[-1]
    description = override.get("description") or ""
    category = derive_category(display_name, description)

    canon = repo_url_from_release(release) or normalize_repo_url(repo_url)
    item = {
        "name": display_name,
        "filename": selected["name"],
        "url": selected["browser_download_url"],
        "description": description,
        "version": release.get("tag_name", ""),
        "category": category,
        "checksum": get_checksum(selected),
        "last_update": format_last_update(release.get("published_at") or ""),
        # Source = repo root URL, straight from release.html_url (no concat).
        "source": canon,
    }
    print(f"  → {selected['name']} @ {release.get('tag_name')} ({category})")
    return item, canon


# ─── README ──────────────────────────────────────────────────────────
def update_readme(payloads: list[dict]) -> None:
    rows = [
        "| Name | Version | Category | Description | Last Updated | Source |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for p in payloads:
        description = (p.get("description") or "No description provided.").replace("|", "\\|")
        source_url = p.get("source", "")
        m = re.search(r"https?://[^/]+/([^/]+)/([^/]+)", source_url)
        source_label = f"{m.group(1)}/{m.group(2)}" if m else "Source"
        last_update = p.get("last_update") or "-"
        rows.append(
            f"| **{p.get('name','')}** | `{p.get('version','')}` | {p.get('category','')} | "
            f"{description} | `{last_update}` | [{source_label}]({source_url}) |"
        )
    table = "\n".join(rows)
    start, end = "<!-- PAYLOADS_START -->", "<!-- PAYLOADS_END -->"
    if not Path(README_FILE).exists():
        return
    with open(README_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    if start in content and end in content:
        pattern = re.compile(f"{re.escape(start)}.*?{re.escape(end)}", re.DOTALL)
        new_content = pattern.sub(f"{start}\n{table}\n{end}", content)
        if new_content == content:
            return  # no change, skip write
        with open(README_FILE, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated {README_FILE}")


# ─── Main ────────────────────────────────────────────────────────────
def main() -> None:
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        sources = json.load(f)
    print(f"Loaded {len(sources)} curated entries from {SOURCES_FILE}")

    discovery = fetch_itsplk_discovery()
    ps5upload = fetch_ps5upload_catalogue()

    # Curation: overrides keyed by lowercased repo URL; `exclude` read from the entry directly.
    overrides = {}
    for src in sources:
        repo_url = src.get("url") or src.get("source", "")
        if not repo_url:
            print(f"warning: sources.json entry without url/source, skipped: {src}")
            continue
        if not parse_repo_url(repo_url):
            print(f"warning: sources.json entry has unparseable url {repo_url!r}, skipped")
            continue
        key = normalize_repo_url(repo_url)
        if key in overrides:
            print(f"warning: duplicate sources.json entry for {repo_url}; last one wins")
        overrides[key] = {**src, "repo_url": repo_url}

    # Union: curated overrides + itsPLK discovery + ps5upload catalogue
    seen = set(overrides.keys())
    all_keys = list(overrides.keys())
    for k in list(discovery.keys()) + list(ps5upload.keys()):
        if k not in seen:
            all_keys.append(k)
            seen.add(k)

    final_items = []
    canon_seen = set()
    n_excluded = 0
    n_deduped = 0
    skipped = []

    for key in all_keys:
        if overrides.get(key, {}).get("exclude"):
            print(f"Excluded by sources.json: {overrides[key].get('repo_url', key)}")
            n_excluded += 1
            continue

        src_override = overrides.get(key, {})
        disc = discovery.get(key, {})
        psu = ps5upload.get(key, {})

        repo_url = (
            src_override.get("repo_url")
            or disc.get("repo_url")
            or psu.get("repo_url")
        )
        if not repo_url:
            continue

        # Merged override with priority: sources.json > ps5upload > itsPLK.
        # `display_name`/`description`/`asset_pattern` come from this merge;
        # `asset_hint` (ps5upload's asset_name_hint) is threaded separately
        # because itsPLK/sources.json use `asset_pattern`, not `asset_name_hint`.
        override = {}
        for field in ("display_name", "description", "asset_pattern"):
            for src_data in (src_override, psu, disc):
                val = src_data.get(field)
                if val:
                    override[field] = val
                    break

        result = build_item(repo_url, override, psu.get("asset_name_hint") or "")
        if not result:
            skipped.append(repo_url)
            continue

        item, canon = result
        if canon in canon_seen:
            print(f"  dedup: {repo_url} folds into {canon}, already listed")
            n_deduped += 1
            continue
        canon_seen.add(canon)
        final_items.append(item)

    final_items.sort(key=lambda p: p.get("name", "").lower())

    document = {"name": CATALOGUE_NAME, "payloads": final_items}
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(document, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(
        f"\nWrote {OUTPUT_FILE}: {len(final_items)} listed, "
        f"{n_excluded} excluded, {n_deduped} deduped, {len(skipped)} skipped"
    )
    if skipped:
        print(f"Skipped: {', '.join(skipped)}")

    update_readme(final_items)


if __name__ == "__main__":
    main()
