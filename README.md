# ps5-payloads-atlas

Aggregated PS5 payload catalogue in [ps5-payload-manager](https://github.com/itsPLK/ps5-payload-manager) custom-repository format.

Data is sourced directly from real upstream release repositories (not mirrors). The aggregator composes three layers:

- **Discovery** — [itsPLK/ps5-payloads-mirror](https://github.com/itsPLK/ps5-payloads-mirror) `payloads.json` supplies the upstream repo list, so new payloads added there appear here automatically.
- **Curation** — `sources.json` overrides display name / description / asset selection per repo, and can `"exclude": true` to suppress a repo entirely.
- **Enrichment** — [phantomptr/ps5upload](https://github.com/phantomptr/ps5upload) `CATALOGUE` provides longer descriptions where available.

A GitHub Action refreshes `payloads.json` hourly.

## Files

- `payloads.json` — the catalogue consumed by ps5-payload-manager (`Settings → Manage Sources → Add Source`, paste the raw URL).
- `sources.json` — curation overlay (override / exclude). Acts as fallback seed if discovery fails.
- `update_payloads.py` — the aggregator.

## Notes

- No binaries are hosted here. `url` points at the upstream release asset; download happens on the PS5 side.
- Checksums come from the GitHub Release API `digest` field. Non-GitHub repos (e.g. Forgejo on `git.etawen.dev`) and assets without a published digest have an empty `checksum`.
- `LightningMods/Itemzflow` is excluded — its releases ship no `.elf`/`.bin` asset.
- Pre-release-only repos fall back to the most recent pre-release.
- Repos are deduped by canonical `(owner, repo)` after redirect resolution (e.g. `LightningMods/etaHEN` folds into `etaHEN/etaHEN`).

<!-- PAYLOADS_START -->
| Name | Version | Category | Description | Last Updated | Source |
| --- | --- | --- | --- | --- | --- |
| **kstuff-lite (EchoStretch)** | `v1.09` | Kernel | Kernel patcher for the full PS5 firmware range. Resolves kernel symbols at runtime via the SDK's NID table, so the same binary covers FW 1.00–12.x. Required by ShadowMountPlus and most other privileged payloads. Load this first. | `2026-07-04` | [Source](https://github.com/echostretch/kstuff-lite/releases) |
| **kstuff-lite (drakmor — fpkg-optimized)** | `1.2-dr-test1` | Kernel | Fork of EchoStretch/kstuff-lite with a hot path for .ffpkg (UFS) + PFS mounts and lower overhead in repeated mount/unmount cycles. Adds an option to disable automatic mounting (noautomount) for a controlled startup. | `2026-05-31` | [Source](https://github.com/drakmor/kstuff-lite/releases) |
| **kstuff** | `v1.6.7` | Kernel | Full build of kstuff: dynamically patches the PS5 kernel to bypass security. | `2026-01-04` | [Source](https://github.com/echostretch/kstuff/releases) |
| **kstuff-toggle** | `0.6` | Kernel | Boost homebrew game performance on your PS5 by disabling Kstuff after launching the game. Ships as a zip; extract kstuff-toggle-3.elf after download. | `2026-05-07` | [Source](https://github.com/echostretch/kstuff-toggle/releases) |
| **ShadowMount+** | `1.6beta16` | Launcher | Fully automated background 'Auto-Mounter' payload for jailbroken PS5. Watches scan folders for game folders and .ffpkg/.exfat/.ffpfs/.ffpfsc images, auto-mounts them, stages sce_sys + appmeta + trophy data, and registers them on the home screen. | `2026-06-28` | [Source](https://github.com/drakmor/shadowmountplus/releases) |
| **etaHEN** | `2.5B` | Kernel | Long-running homebrew enabler with toolbox features. Faster app jailbreak than the on-the-fly path; provides the HijackerCommand IPC many homebrew apps expect on :9028. | `2025-12-25` | [Source](https://github.com/etahen/etahen/releases) |
| **ftpsrv** | `v0.20` | File Transfer | Lightweight FTP server on :2121 with SELF/ELF auto-decryption and remount-RW SITE commands. Browse the PS5 filesystem from any FTP client. | `2026-05-12` | [Source](https://github.com/ps5-payload-dev/ftpsrv/releases) |
| **ftpsrv (drakmor)** | `1.15-ng-stable` | Misc | drakmor's fork of ftpsrv. | `2026-04-08` | [Source](https://github.com/drakmor/ftpsrv/releases) |
| **websrv** | `v0.33` | Networking | HTTP server on :8080 serving a homebrew launcher page. Pairs with the homebrew bundles distributed by ps5-payload-dev. | `2026-06-28` | [Source](https://github.com/ps5-payload-dev/websrv/releases) |
| **shsrv** | `v0.19` | Networking | Telnet server on :2323 with 42 POSIX-ish commands plus hbldr (launch unsigned ELF with full A/V) and hbdbg (gdb-style debugger). | `2026-06-28` | [Source](https://github.com/ps5-payload-dev/shsrv/releases) |
| **klogsrv** | `v0.8` | Launcher | Streams /dev/klog over TCP :3232 and tees it to /data/klog/klog.log (10-backup rotation). | `2026-05-12` | [Source](https://github.com/ps5-payload-dev/klogsrv/releases) |
| **elfldr** | `v0.23` | Launcher | An ELF loader for jailbroken PS5s that accepts payloads on port 9021. | `2026-05-12` | [Source](https://github.com/ps5-payload-dev/elfldr/releases) |
| **ps5-app-dumper** | `v1.10` | Launcher | Dumps installed PS5 apps to USB or internal storage in fakepkg/folder format. Reads config from /data/ps5-app-dumper/config.ini. | `2026-05-03` | [Source](https://github.com/echostretch/ps5-app-dumper/releases) |
| **nanoDNS** | `0.3` | Networking | Minimal DNS server running on the PS5 (UDP :53). Blocks PlayStation Network + update domains by default and can redirect any domain to a LAN IP. | `2026-06-03` | [Source](https://github.com/drakmor/nanodns/releases) |
| **Ghostpad** | `v1.0.0` | Misc | Creates a virtual PS5 controller on the console and redirects input to it — useful for input automation, remote control, and accessibility setups. | `2026-05-31` | [Source](https://github.com/stonedmodder/ghostpad/releases) |
| **ezremote-DPI** | `1.04` | Launcher | Long-lived loopback PKG install daemon (127.0.0.1:9040). Owns Sony's PlayGo/AppInstUtil install state machine so installs don't evaporate when the calling process exits. | `2025-07-01` | [Source](https://github.com/cy33hc/ps5-ezremote-dpi/releases) |
| **CheatRunner** | `v0.14` | Misc | Loads and applies game cheats on the PS5. Send it like any other payload, then browse and toggle cheats for supported titles on the console. | `2026-06-18` | [Source](https://github.com/notmaj0r/cheatrunner/releases) |
| **Lapy JB Daemon** | `v1.2` | Kernel | Standalone homebrew jailbreak daemon for PS5. Mimics etaHEN's jailbreak-on-demand API. Multi-firmware (3.00 to 12.00). No etaHEN required. Upstream voidwhisper/lapy-jb-daemon on git.etawen.dev is offline; this GitHub mirror is the live source. | `2026-06-01` | [Source](https://github.com/itsplk/ps5-lapy-jb-daemon/releases) |
| **ps5debug-NG** | `1.3.0` | Debugger | PS5 debugger payload — userland TCP wire-protocol server hosted inside SceShellCore. | `2026-06-21` | [Source](https://github.com/opensourcerer-dev/ps5debug-ng/releases) |
| **zftpd** | `v1.5.0` | File Transfer | Zero-copy FTP/HTTP server. | `2026-06-14` | [Source](https://github.com/seregonwar/zftpd/releases) |
| **pldmgr** | `v0.3.1` | Networking | A modern, web-based dashboard to easily manage, import, and automatically load payloads on your PS5. | `2026-06-06` | [Source](https://github.com/itsplk/ps5-payload-manager/releases) |
| **ps5-linux-loader** | `v2.3` | Kernel | Linux payload implementing HV exploits to run a custom bootloader. | `2026-07-01` | [Source](https://github.com/ps5-linux/ps5-linux-loader/releases) |
| **BackPork** | `0.1` | Misc | Lets you sideload system libraries into PS5 games. | `2026-04-30` | [Source](https://github.com/bestpig/backpork/releases) |
| **Garlic Worker** | `v1.1.6` | Save Manager | Background worker that drains the community save-decryption queue from garlicsaves.com. Handles both PS4 and PS5 saves natively. Opt-in: connects to garlicsaves.com. | `2026-07-04` | [Source](https://git.etawen.dev/earthonion/garlic-worker/releases) |
| **Garlic SaveMgr** | `v1.10` | Save Manager | On-console save decrypt/encrypt daemon. Back up saves in plaintext, edit on PC, re-encrypt for the same console. No network. | `2026-06-11` | [Source](https://git.etawen.dev/earthonion/garlic-savemgr/releases) |
| **NP Fake Sign-in** | `v1.3` | Misc | Headless payload that registers PS5 user slots directly via the system registry. Offline account activation without PSN. One-shot ELF: send, runs, exits. | `2026-05-15` | [Source](https://git.etawen.dev/earthonion/np-fake-signin/releases) |
<!-- PAYLOADS_END -->

## Support & Suggestions

If you have suggestions for a new payload or a payload is mis-categorised, please open an issue.
