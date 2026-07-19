# ps5-payloads-atlas

Aggregated PS5 payload catalogue in [ps5-payload-manager](https://github.com/itsPLK/ps5-payload-manager) custom-repository format.

Data is sourced directly from real upstream release repositories (not mirrors). The aggregator composes three layers:

- **Discovery** — the upstream repo list is the union of [itsPLK/ps5-payloads-mirror](https://github.com/itsPLK/ps5-payloads-mirror) `payloads.json` and [phantomptr/ps5upload](https://github.com/phantomptr/ps5upload) `CATALOGUE`. Both are first-class sources; new payloads in either appear here automatically.
- **Curation** — `sources.json` overrides display name / description / asset selection per repo, and can `"exclude": true` to suppress a repo entirely.
- **Enrichment** — `phantomptr/ps5upload` `CATALOGUE` provides longer descriptions / display names where available.

**A GitHub Action refreshes `payloads.json` hourly.**

## Files

- `payloads.json` — the catalogue consumed by ps5-payload-manager (`Settings → Manage Sources → Add Source`, paste the raw URL).
- `sources.json` — curation overlay (override / exclude). Acts as fallback seed if discovery fails.
- `update_payloads.py` — the aggregator.

## `sources.json` schema

Each entry is one upstream repo. Only `url` is required; every other field is an optional override with the fallback shown.

| Field | Required | Purpose | Fallback if omitted |
| --- | --- | --- | --- |
| `url` | yes | Repo HTML URL — the entry's identity and API lookup key | — |
| `display_name` | no | Overrides the output `name` | ps5upload `display_name` → repo name from URL |
| `description` | no | Overrides the output `description` | ps5upload / itsPLK description → empty |
| `asset_pattern` | no | Regex narrowing which release asset to pick (multiple `.elf` files) | ps5upload `asset_name_hint` → no filter |
| `exclude` | no | `true` skips this repo entirely | `false` (include) |

Same repo under multiple aliases (e.g. `LightningMods/etaHEN` and `etaHEN/etaHEN`) needs one entry per alias if you want to override or exclude both.

## Notes

- This repository aggregates **metadata only** (name, description, version, checksum, download URL) about third-party PS5 payload projects. The upstream payloads themselves remain the property of their respective authors under their own licenses. The MIT license above covers only the aggregation script, the curated `sources.json`, and the generated `payloads.json`.
- No binaries are hosted here. `url` points at the upstream release asset; download happens on the PS5 side.
- Checksums come from the GitHub Release API `digest` field. Non-GitHub repos (e.g. Forgejo on `git.etawen.dev`) and assets without a published digest have an empty `checksum`.
- `LightningMods/Itemzflow` is auto-skipped — its releases ship no `.elf`/`.bin` asset, so the aggregator finds no canonical asset to list.
- Pre-release-only repos fall back to the most recent pre-release.
- Repos are deduped by canonical `(owner, repo)` after redirect resolution (e.g. `LightningMods/etaHEN` folds into `etaHEN/etaHEN`).

<!-- PAYLOADS_START -->
| Name | Version | Category | Description | Last Updated | Source |
| --- | --- | --- | --- | --- | --- |
| **BackPork** | `0.1` | Misc | Lets you sideload system libraries into PS5 games. | `2026-05-01 00:34:19 UTC+8` | [bestpig/backpork](https://github.com/bestpig/backpork) |
| **CheatRunner** | `v0.15` | Misc | Loads and applies game cheats on the PS5. Send it like any other payload, then browse and toggle cheats for supported titles on the console. | `2026-07-08 03:30:55 UTC+8` | [notmaj0r/cheatrunner](https://github.com/notmaj0r/cheatrunner) |
| **elfldr** | `v0.23` | Launcher | An ELF loader for jailbroken PS5s that accepts payloads on port 9021. | `2026-05-13 02:51:52 UTC+8` | [ps5-payload-dev/elfldr](https://github.com/ps5-payload-dev/elfldr) |
| **ezremote-DPI** | `1.04` | Launcher | Long-lived loopback PKG install daemon (127.0.0.1:9040). Owns Sony's PlayGo/AppInstUtil install state machine so installs don't evaporate when the calling process exits. | `2025-07-02 03:42:24 UTC+8` | [cy33hc/ps5-ezremote-dpi](https://github.com/cy33hc/ps5-ezremote-dpi) |
| **ftpsrv** | `v0.20` | File Transfer | Lightweight FTP server on :2121 with SELF/ELF auto-decryption and remount-RW SITE commands. Browse the PS5 filesystem from any FTP client. | `2026-05-13 02:36:49 UTC+8` | [ps5-payload-dev/ftpsrv](https://github.com/ps5-payload-dev/ftpsrv) |
| **ftpsrv (drakmor)** | `1.15-ng-stable` | File Transfer | drakmor's fork of ftpsrv. | `2026-04-08 10:17:12 UTC+8` | [drakmor/ftpsrv](https://github.com/drakmor/ftpsrv) |
| **Garlic SaveMgr** | `v1.12` | Save Manager | On-console save decrypt/encrypt daemon. Back up saves in plaintext, edit on PC, re-encrypt for the same console. No network. | `2026-07-14 06:57:50 UTC+8` | [earthonion/garlic-savemgr](https://git.etawen.dev/earthonion/garlic-savemgr) |
| **Garlic Worker** | `v1.1.6` | Save Manager | Background worker that drains the community save-decryption queue from garlicsaves.com. Handles both PS4 and PS5 saves natively. Opt-in: connects to garlicsaves.com. | `2026-07-04 21:24:04 UTC+8` | [earthonion/garlic-worker](https://git.etawen.dev/earthonion/garlic-worker) |
| **Ghostpad** | `v1.0.0` | Misc | Creates a virtual PS5 controller on the console and redirects input to it — useful for input automation, remote control, and accessibility setups. | `2026-05-31 23:27:41 UTC+8` | [stonedmodder/ghostpad](https://github.com/stonedmodder/ghostpad) |
| **klogsrv** | `v0.8` | Networking | Streams /dev/klog over TCP :3232 and tees it to /data/klog/klog.log (10-backup rotation). | `2026-05-13 02:44:28 UTC+8` | [ps5-payload-dev/klogsrv](https://github.com/ps5-payload-dev/klogsrv) |
| **kstuff** | `v1.6.7` | Kernel | Full build of kstuff: dynamically patches the PS5 kernel to bypass security. | `2026-01-04 23:55:09 UTC+8` | [echostretch/kstuff](https://github.com/echostretch/kstuff) |
| **kstuff-lite (drakmor — fpkg-optimized)** | `1.2-dr-test1` | Kernel | Fork of EchoStretch/kstuff-lite with a hot path for .ffpkg (UFS) + PFS mounts and lower overhead in repeated mount/unmount cycles. Adds an option to disable automatic mounting (noautomount) for a controlled startup. | `2026-05-31 21:18:16 UTC+8` | [drakmor/kstuff-lite](https://github.com/drakmor/kstuff-lite) |
| **kstuff-lite (EchoStretch)** | `v1.09` | Kernel | Kernel patcher for the full PS5 firmware range. Resolves kernel symbols at runtime via the SDK's NID table, so the same binary covers FW 1.00–12.x. Required by ShadowMountPlus and most other privileged payloads. Load this first. | `2026-07-04 09:30:05 UTC+8` | [echostretch/kstuff-lite](https://github.com/echostretch/kstuff-lite) |
| **Lapy JB Daemon** | `v1.2` | Kernel | Standalone homebrew jailbreak daemon for PS5. Mimics etaHEN's jailbreak-on-demand API. Multi-firmware (3.00 to 12.00). No etaHEN required. Upstream voidwhisper/lapy-jb-daemon on git.etawen.dev is offline; this GitHub mirror is the live source. | `2026-06-02 02:26:02 UTC+8` | [itsplk/ps5-lapy-jb-daemon](https://github.com/itsplk/ps5-lapy-jb-daemon) |
| **nanoDNS** | `0.3` | Networking | Minimal DNS server running on the PS5 (UDP :53). Blocks PlayStation Network + update domains by default and can redirect any domain to a LAN IP. | `2026-06-03 17:37:48 UTC+8` | [drakmor/nanodns](https://github.com/drakmor/nanodns) |
| **NP Fake Sign-in** | `v1.3` | Misc | Headless payload that registers PS5 user slots directly via the system registry. Offline account activation without PSN. One-shot ELF: send, runs, exits. | `2026-05-15 19:41:36 UTC+8` | [earthonion/np-fake-signin](https://git.etawen.dev/earthonion/np-fake-signin) |
| **pldmgr** | `v0.4.0` | Misc | A modern, web-based dashboard to easily manage, import, and automatically load payloads on your PS5. | `2026-07-19 23:20:31 UTC+8` | [itsplk/ps5-payload-manager](https://github.com/itsplk/ps5-payload-manager) |
| **ps5-app-dumper** | `v1.10` | Dumper | Dumps installed PS5 apps to USB or internal storage in fakepkg/folder format. Reads config from /data/ps5-app-dumper/config.ini. | `2026-05-04 05:51:19 UTC+8` | [echostretch/ps5-app-dumper](https://github.com/echostretch/ps5-app-dumper) |
| **ps5-linux-loader** | `v2.4` | Kernel | Linux payload implementing HV exploits to run a custom bootloader. | `2026-07-06 16:03:05 UTC+8` | [ps5-linux/ps5-linux-loader](https://github.com/ps5-linux/ps5-linux-loader) |
| **ps5debug-NG** | `1.3.0` | Debugger | PS5 debugger payload — userland TCP wire-protocol server hosted inside SceShellCore. | `2026-06-21 15:37:35 UTC+8` | [opensourcerer-dev/ps5debug-ng](https://github.com/opensourcerer-dev/ps5debug-ng) |
| **ShadowMount+** | `1.6beta16` | Launcher | Fully automated background 'Auto-Mounter' payload for jailbroken PS5. Watches scan folders for game folders and .ffpkg/.exfat/.ffpfs/.ffpfsc images, auto-mounts them, stages sce_sys + appmeta + trophy data, and registers them on the home screen. | `2026-06-28 21:59:58 UTC+8` | [drakmor/shadowmountplus](https://github.com/drakmor/shadowmountplus) |
| **shsrv** | `v0.19` | Networking | Telnet server on :2323 with 42 POSIX-ish commands plus hbldr (launch unsigned ELF with full A/V) and hbdbg (gdb-style debugger). | `2026-06-29 00:21:35 UTC+8` | [ps5-payload-dev/shsrv](https://github.com/ps5-payload-dev/shsrv) |
| **websrv** | `v0.33` | Networking | HTTP server on :8080 serving a homebrew launcher page. Pairs with the homebrew bundles distributed by ps5-payload-dev. | `2026-06-28 23:54:38 UTC+8` | [ps5-payload-dev/websrv](https://github.com/ps5-payload-dev/websrv) |
| **zftpd** | `v1.5.0` | File Transfer | Zero-copy FTP/HTTP server. | `2026-06-15 01:25:58 UTC+8` | [seregonwar/zftpd](https://github.com/seregonwar/zftpd) |
<!-- PAYLOADS_END -->

## Support & Suggestions

If you have suggestions for a new payload or a payload is mis-categorised, please open an issue.
