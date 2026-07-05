# ps5-payload-catalogue

Aggregated PS5 payload catalogue in [ps5-payload-manager](https://github.com/itsPLK/ps5-payload-manager) custom-repository format.

Data is sourced directly from real upstream release repositories (not mirrors). The catalogue merges entries discovered in:

- [itsPLK/ps5-payloads-mirror](https://github.com/itsPLK/ps5-payloads-mirror)
- [phantomptr/ps5upload](https://github.com/phantomptr/ps5upload) (`payloads.rs` CATALOGUE)

A GitHub Action refreshes `payloads.json` daily at 00:00 UTC.

## Files

- `payloads.json` — the catalogue consumed by ps5-payload-manager (`Settings → Manage Sources → Add Source`, paste the raw URL).
- `sources.json` — curated seed list of upstream repos that the aggregator reads.
- `update_payloads.py` — the aggregator.

## Notes

- Checksums come from the GitHub Release API `digest` field. Non-GitHub repos (e.g. Forgejo on `git.etawen.dev`) and assets without a published digest have an empty `checksum`.
- `LightningMods/Itemzflow` is intentionally excluded — its releases ship no `.elf`/`.bin` asset.
- Pre-release-only repos fall back to the most recent pre-release.

<!-- PAYLOADS_START -->
| Name | Version | Category | Description | Last Updated | Source |
| --- | --- | --- | --- | --- | --- |
| **kstuff-lite (EchoStretch)** | `v1.09` | Kernel | Kernel patcher for the full PS5 firmware range. Resolves kernel symbols at runtime via the SDK's NID table, so the same binary covers FW 1.00 → 12.x. Required by ShadowMountPlus and most other privileged payloads. Load this first. | `2026-07-04` | [Source](https://github.com/EchoStretch/kstuff-lite/releases) |
| **kstuff-lite (drakmor — fpkg-optimized)** | `1.2-dr-test1` | Kernel | Fork of EchoStretch/kstuff-lite with a hot path for .ffpkg (UFS) + PFS mounts and lower overhead in repeated mount/unmount cycles. Recent builds extended firmware coverage through FW 12.xx (the '12.xx Support' update) on top of the original 3.00→10.01 range — check the release notes for your exact firmware. Adds an option to disable automatic mounting (noautomount) for a controlled startup. Recommended when your primary workflow is ShadowMount+ with .ffpkg/.exfat/PFS images. Same load-first ordering as any other kstuff: must boot before ShadowMount+ or ps5upload. | `2026-05-31` | [Source](https://github.com/drakmor/kstuff-lite/releases) |
| **kstuff** | `v1.6.7` | Kernel | Full build of kstuff: dynamically patches the PS5 kernel to bypass security. | `2026-01-04` | [Source](https://github.com/EchoStretch/kstuff/releases) |
| **kstuff-toggle** | `0.6` | Kernel | Boost homebrew game performance on your PS5 by disabling Kstuff after launching the game. Ships as a zip; extract kstuff-toggle-3.elf after download. | `2026-05-07` | [Source](https://github.com/EchoStretch/kstuff-toggle/releases) |
| **ShadowMount+** | `1.6beta16` | Kernel | Watches scan folders (/mnt/usb*, /mnt/ext*, /data/homebrew, /mnt/shadowmnt) AND /data/shadowmount/manual.lst for game folders and .ffpkg/.exfat/.ffpfs/.ffpfsc images, then auto-mounts (LVD/MD), stages sce_sys + appmeta + trophy data, and registers them on the home screen — no per-image command, it's fully autonomous. Newer builds add nested/compressed-PFS (.ffpfsc) containers, trophy-data copy, and a watched manual-install list. Includes fakelib (backports) overlay + per-game kstuff autopause. Needs kstuff-lite v1.07+ loaded first. | `2026-06-28` | [Source](https://github.com/drakmor/ShadowMountPlus/releases) |
| **etaHEN** | `2.5B` | Kernel | Long-running homebrew enabler with toolbox features. Faster app jailbreak than the on-the-fly path; provides the HijackerCommand IPC many homebrew apps expect on :9028. | `2025-12-25` | [Source](https://github.com/etaHEN/etaHEN/releases) |
| **ftpsrv** | `v0.20` | File Transfer | Lightweight FTP server on :2121 with SELF↔ELF auto-decryption and remount-RW SITE commands. Lets you browse the PS5's filesystem from any FTP client. | `2026-05-12` | [Source](https://github.com/ps5-payload-dev/ftpsrv/releases) |
| **ftpsrv (drakmor)** | `1.15-ng-stable` | Misc | drakmor's fork of ftpsrv. | `2026-04-08` | [Source](https://github.com/drakmor/ftpsrv/releases) |
| **websrv** | `v0.33` | Networking | HTTP server on :8080 serving a homebrew launcher page. Pairs with the homebrew bundles distributed by ps5-payload-dev. | `2026-06-28` | [Source](https://github.com/ps5-payload-dev/websrv/releases) |
| **shsrv (telnet shell + ELF launcher + gdb)** | `v0.19` | Networking | Telnet server on :2323 with 42 POSIX-ish commands (sfoinfo, file, hexdump, find with -exec, etc.) plus hbldr (launch unsigned ELF with full A/V) and hbdbg (gdb-style debugger). Our Shell tab covers the same 42 built-ins via :9114 authenticated FTX2; install shsrv if you want hbldr/hbdbg or you prefer telnet access. Connect via `telnet <ps5-ip> 2323`. | `2026-06-28` | [Source](https://github.com/ps5-payload-dev/shsrv/releases) |
| **klogsrv** | `v0.8` | Kernel | Streams /dev/klog over TCP :3232 and tees it to /data/klog/klog.log (10-backup rotation). Useful for capturing kernel-log activity that happens while the ps5upload desktop app is closed, or for tailing klog via plain netcat without our payload. | `2026-05-12` | [Source](https://github.com/ps5-payload-dev/klogsrv/releases) |
| **elfldr** | `v0.23` | Launcher | An ELF loader for jailbroken PS5s that accepts payloads on port 9021. | `2026-05-12` | [Source](https://github.com/ps5-payload-dev/elfldr/releases) |
| **ps5-app-dumper** | `v1.10` | Launcher | Dumps installed PS5 apps to USB or internal storage in fakepkg/folder format. Reads config from /data/ps5-app-dumper/config.ini. | `2026-05-03` | [Source](https://github.com/EchoStretch/ps5-app-dumper/releases) |
| **nanoDNS** | `0.3` | Networking | A minimal DNS server that runs on the PS5 (UDP :53). Ships blocking PlayStation Network + update domains by default (0.0.0.0), and can redirect any domain to a LAN IP — handy for staying offline-friendly while jailbroken. Point the console's DNS at it (set bind=0.0.0.0 in the ini to serve the LAN). Config: /data/nanodns/nanodns.ini (auto-created with sane defaults). PS5 build only — never the -ps4 asset. | `2026-06-03` | [Source](https://github.com/drakmor/nanoDNS/releases) |
| **Ghostpad** | `v1.0.0` | Misc | Creates a virtual PS5 controller on the console and redirects input to it — useful for input automation, remote control, and accessibility setups. Send the payload to start it; pair it with the upstream's companion app for driving the virtual pad. | `2026-05-31` | [Source](https://github.com/StonedModder/Ghostpad/releases) |
| **ezremote-DPI (install daemon)** | `1.04` | Launcher | Long-lived loopback install daemon (127.0.0.1:9040). Owns Sony's PlayGo/AppInstUtil install state machine so installs don't evaporate when the calling process exits. Sonicloader and ezremote-client both use this as their primary install path. Once installed, ps5upload's install runner will offer a 'DPI' method that proxies to it (planned for follow-up). | `2025-07-01` | [Source](https://github.com/cy33hc/ps5-ezremote-dpi/releases) |
| **CheatRunner** | `v0.14` | Misc | Loads and applies game cheats on the PS5. Send it like any other payload, then browse and toggle cheats for supported titles on the console. | `2026-06-18` | [Source](https://github.com/notmaj0r/CheatRunner/releases) |
| **Lapy JB Daemon** | `v1.2` | Kernel | Standalone homebrew jailbreak daemon for PS5. Mimics etaHEN's jailbreak-on-demand API. Multi-firmware (3.00 to 12.00). No etaHEN required. Upstream voidwhisper/lapy-jb-daemon on git.etawen.dev is offline; this GitHub mirror is the live source. | `2026-06-01` | [Source](https://github.com/itsPLK/PS5-Lapy-JB-Daemon/releases) |
| **ps5debug-NG** | `1.3.0` | Debugger | PS5 debugger payload — userland TCP wire-protocol server hosted inside SceShellCore. | `2026-06-21` | [Source](https://github.com/OpenSourcereR-dev/ps5debug-NG/releases) |
| **zftpd** | `v1.5.0` | File Transfer | Zero-copy FTP/HTTP server. | `2026-06-14` | [Source](https://github.com/seregonwar/zftpd/releases) |
| **pldmgr** | `v0.3.1` | Networking | A modern, web-based dashboard to easily manage, import, and automatically load payloads on your PS5. | `2026-06-06` | [Source](https://github.com/itsPLK/pldmgr/releases) |
| **ps5-linux-loader** | `v2.3` | Kernel | Linux payload implementing HV exploits to run a custom bootloader. | `2026-07-01` | [Source](https://github.com/ps5-linux/ps5-linux-loader/releases) |
| **BackPork** | `0.1` | Misc | Lets you sideload system libraries into PS5 games. | `2026-04-30` | [Source](https://github.com/BestPig/BackPork/releases) |
| **Garlic Worker (community save processor)** | `v1.1.6` | Save Manager | Background worker that drains the community save-decryption queue from garlicsaves.com. Handles both PS4 and PS5 saves natively. **Privacy notice**: connects to garlicsaves.com and processes other users' encrypted save files. Off by default — install + run manually if you want to contribute back to the community queue. | `2026-07-04` | [Source](https://git.etawen.dev/earthonion/garlic-worker/releases) |
| **Garlic SaveMgr (decrypt your own saves)** | `v1.10` | Save Manager | On-console save decrypt/encrypt daemon. Lets you back up saves in plaintext, edit them on PC, and re-encrypt for the same console. No network — operates purely on saves you already own. Companion to ps5upload's Saves tab; install this for round-trip plaintext editing workflows. | `2026-06-11` | [Source](https://git.etawen.dev/earthonion/garlic-savemgr/releases) |
| **NP Fake Sign-in** | `v1.3` | Kernel | Headless payload that registers PS5 user slots directly via the system registry. Replaces having to sign into a real PSN account just to set up local users — handy for fresh jailbreaks, secondary accounts, or test profiles. One-shot ELF: send, runs, exits. | `2026-05-15` | [Source](https://git.etawen.dev/earthonion/np-fake-signin/releases) |
<!-- PAYLOADS_END -->

## Support & Suggestions

If you have suggestions for a new payload or a payload is mis-categorised, please open an issue.
