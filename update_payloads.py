#!/usr/bin/env python3
"""Aggregate PS5 payload catalogue into payloads.json.

Three-layer composition, all read-only against upstream:
  1. Discovery: `itsPLK/ps5-payloads-mirror/payloads.json` supplies the upstream
     repo list (so new payloads added there appear here automatically).
  2. Curation: `sources.json` overrides display name / description /
     asset_pattern / extract_file for any repo, and can `exclude` repos we do
     not want to republish. Entries here also act as a fallback seed if the
     itsPLK discovery fetch fails.
  3. Enrichment: `phantomptr/ps5upload` `CATALOGUE` provides longer
     descriptions / display names where available.

For each repo, the latest release is queried, the canonical asset is picked,
and an entry in ps5-payload-manager custom-repository schema is emitted.

Notes:
- No binaries are downloaded. GitHub checksums come from the Release API
  `digest` field. Forgejo / missing-digest assets get an empty checksum.
- `/releases/latest` 404 → fall back to `/releases[0]` for pre-release-only repos.
- Repos are deduped by canonical (host, owner, repo) after redirect resolution
  (e.g. LightningMods/etaHEN folds into etaHEN/etaHEN).
"""

import json
import re
import subprocess
import urllib.request
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
CATALOGUE_NAME = "PS5 Payload Catalogue"


# ─── HTTP helpers ──────────────────────────────────────────────────────
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
        url = f"https://{host}/api/v1/{endpoint}"
        return json.loads(http_get(url))
    except Exception as e:
        print(f"  forgejo {url} failed: {e}")
        return None


def get_latest_release(host: str, owner: str, repo: str) -> dict | None:
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


# ─── Repo URL / canonical resolution ─────────────────────────────────
def parse_repo_url(url: str):
    m = re.search(r"https?://([^/]+)/([^/]+)/([^/?#]+)", url or "")
    if not m:
        return None
    host, owner, repo = m.groups()
    repo = repo.rstrip("/")
    if repo.endswith(".git"):
        repo = repo[:-4]
    if repo.lower() == "releases":
        parts = (url or "").split("/")
        try:
            idx = parts.index(host)
            owner, repo = parts[idx + 1], parts[idx + 2]
        except (ValueError, IndexError):
            return None
    return host, owner, repo


def canonical_key(host: str, owner: str, repo: str, release: dict) -> tuple:
    """Resolve redirects via the release's API url; fall back to input."""
    if host == "github.com":
        url = release.get("url", "")
        m = re.search(r"/repos/([^/]+)/([^/]+)/releases/", url)
        if m:
            return (host, m.group(1).lower(), m.group(2).lower())
    return (host, owner.lower(), repo.lower())


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


# ─── Discovery: itsPLK payloads.json ─────────────────────────────────
def fetch_itsplk_discovery() -> dict:
    """Return {(host, owner_lower, repo_lower): {host, owner, repo, name, description}}."""
    try:
        data = json.loads(http_get(ITSPLK_DISCOVERY_URL, timeout=30))
    except Exception as e:
        print(f"itsPLK discovery fetch failed (continuing from sources.json only): {e}")
        return {}
    discovered = {}
    for p in data:
        info = parse_repo_url(p.get("source", ""))
        if not info:
            continue
        host, owner, repo = info
        key = (host, owner.lower(), repo.lower())
        discovered[key] = {
            "host": host,
            "owner": owner,
            "repo": repo,
            "display_name": p.get("name"),
            "description": p.get("description") or "",
            "asset_pattern": p.get("asset_pattern") or "",
            "extract_file": p.get("extract_file"),
        }
    print(f"itsPLK discovery loaded: {len(discovered)} repos")
    return discovered


# ─── Enrichment: ps5upload CATALOGUE ─────────────────────────────────
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
    m = re.search(rf"\b{re.escape(key)}\s*:\s*\"([^\"]*)\"", entry)
    return m.group(1) if m else None


def fetch_ps5upload_catalogue() -> dict:
    """Return {(host, owner_lower, repo_lower): {host, owner, repo, display_name, description, asset_name_hint}}.

    The ps5upload CATALOGUE is used both for discovery (the repos it lists) and
    for enrichment (the descriptions / display names it carries).
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
        catalogue[(host, owner.lower(), repo.lower())] = {
            "host": host,
            "owner": owner,
            "repo": repo,
            "display_name": parse_catalogue_str(entry_text, "display_name"),
            "description": parse_catalogue_str(entry_text, "description"),
            "asset_name_hint": parse_catalogue_str(entry_text, "asset_name_hint") or "",
        }
    print(f"ps5upload catalogue loaded: {len(catalogue)} entries")
    return catalogue


# ─── Item builder ────────────────────────────────────────────────────
def build_item(host: str, owner: str, repo: str, override: dict, enrich: dict) -> dict | None:
    """Fetch release, pick asset, emit schema item. Returns item + canon_key via _canon."""
    asset_pattern = override.get("asset_pattern") or enrich.get("asset_name_hint") or ""
    has_extract = bool(override.get("extract_file"))
    preferred_ext = ".bin" if repo.lower() == "etahen" else ".elf"

    print(f"Checking {owner}/{repo} on {host}...")
    release = get_latest_release(host, owner, repo)
    if not release:
        print("  no release found, skipping")
        return None
    canon = canonical_key(host, owner, repo, release)

    assets = release.get("assets", [])
    if not assets:
        print(f"  no assets in release {release.get('tag_name')}, skipping")
        return None

    selected = pick_asset(assets, asset_pattern, has_extract, preferred_ext)
    if not selected:
        print(f"  no suitable asset for {owner}/{repo}, skipping")
        return None

    display_name = (
        override.get("display_name")
        or enrich.get("display_name")
        or repo
    )
    description = (
        override.get("description")
        or enrich.get("description")
        or ""
    )
    category = derive_category(display_name, description)
    checksum = get_checksum(selected, host)

    item = {
        "name": display_name,
        "filename": selected["name"],
        "url": selected["browser_download_url"],
        "description": description,
        "version": release.get("tag_name", ""),
        "category": category,
        "checksum": checksum,
        "last_update": release.get("published_at") or "",
        "source": f"https://{canon[0]}/{canon[1]}/{canon[2]}/releases",
        "_canon": canon,
    }
    print(f"  → {selected['name']} @ {release.get('tag_name')} ({category})")
    return item


# ─── README ──────────────────────────────────────────────────────────
def update_readme(payloads: list[dict]) -> None:
    rows = [
        "| Name | Version | Category | Description | Last Updated | Source |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for p in payloads:
        description = (p.get("description") or "No description provided.").replace("|", "\\|")
        source_url = p.get("source", "")
        m = re.search(r"https?://[^/]+/([^/]+)/([^/]+)/releases", source_url)
        source_label = f"{m.group(1)}/{m.group(2)}" if m else "Source"
        rows.append(
            f"| **{p.get('name','')}** | `{p.get('version','')}` | {p.get('category','')} | "
            f"{description} | `{p.get('last_update','')}` | [{source_label}]({source_url}) |"
        )
    table = "\n".join(rows)
    start, end = "<!-- PAYLOADS_START -->", "<!-- PAYLOADS_END -->"
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


# ─── Main ────────────────────────────────────────────────────────────
def main() -> None:
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        sources = json.load(f)
    print(f"Loaded {len(sources)} curated entries from {SOURCES_FILE}")

    discovery = fetch_itsplk_discovery()
    ps5upload = fetch_ps5upload_catalogue()

    # sources.json: keyed dict + exclude set
    overrides = {}
    excludes = set()
    for src in sources:
        key = (src["host"], src["owner"].lower(), src["repo"].lower())
        overrides[key] = src
        if src.get("exclude"):
            excludes.add(key)

    # Union of repos to consider: curated + itsPLK discovery + ps5upload catalogue
    seen = set(overrides.keys())
    all_keys = list(overrides.keys())
    for k in list(discovery.keys()) + list(ps5upload.keys()):
        if k not in seen:
            all_keys.append(k)
            seen.add(k)

    final_items = []
    canon_seen = set()
    skipped = []

    for key in all_keys:
        src_override = overrides.get(key, {})
        disc = discovery.get(key, {})
        psu = ps5upload.get(key, {})

        # Resolve host/owner/repo (sources.json wins for stability)
        identity = src_override or disc or psu
        if not identity:
            continue
        host = identity["host"]
        owner = identity["owner"]
        repo = identity["repo"]

        # Build merged override with priority: sources.json > ps5upload > itsPLK
        override = {}
        for field in ("display_name", "description", "asset_pattern", "extract_file"):
            for src_data in (src_override, psu, disc):
                val = src_data.get(field)
                if val:
                    override[field] = val
                    break

        item = build_item(host, owner, repo, override, psu)
        if not item:
            skipped.append(f"{owner}/{repo}")
            continue

        canon = item.pop("_canon")
        # Exclude by either the alias key or the resolved canonical key, so an
        # exclude on etaHEN/etaHEN also catches the LightningMods/etaHEN alias.
        if key in excludes or canon in excludes:
            print(f"Excluded: {owner}/{repo} (canon {canon[1]}/{canon[2]})")
            continue
        if canon in canon_seen:
            print(f"  dedup: {owner}/{repo} folds into {canon[1]}/{canon[2]}, already listed")
            continue
        canon_seen.add(canon)
        final_items.append(item)

    final_items.sort(key=lambda p: p.get("name", "").lower())

    document = {"name": CATALOGUE_NAME, "payloads": final_items}
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(document, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {OUTPUT_FILE} ({len(final_items)} payloads, {len(skipped)} skipped)")
    if skipped:
        print(f"Skipped: {', '.join(skipped)}")

    update_readme(final_items)


if __name__ == "__main__":
    main()
