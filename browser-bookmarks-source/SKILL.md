---
name: browser-bookmarks-source
description: Collect bookmarks from all browsers on a source machine into the shared url-groups format during a user migration. Detects installed browsers, dispatches to per-browser extraction leaf skills, and packages the result. Use on the SOURCE machine when migrating bookmarks. Does not implement browser-specific extraction itself.
license: GPL-3.0-or-later
compatibility: opencode
metadata:
  family: user-migration
  tier: logic
  datatype: bookmarks
  direction: source
  leaf_pattern: <browser>-bookmarks-extraction
---

# browser-bookmarks-source

**Tier-1 logic skill.** You own the *bookmarks-collection logic* for a migration
SOURCE: detect which browsers exist, dispatch to the matching per-browser
**extraction leaf** for each, and package every browser's bookmarks into the
shared **url-groups** format. You do NOT read any browser's files directly — that
is the leaf's job.

Read the format contract first: `FORMAT.md` (canonical envelope; bookmarks =
`state: "inactive"`, grouped by folder).

This skill is invoked by the `user-migration-source` orchestrator. It belongs to
a flat skill family with a *logical* hierarchy:

```
user-migration-source                (orchestrator)
└── browser-bookmarks-source         (this skill — logic + format)
    ├── firefox-bookmarks-extraction (leaf — mechanics; covers LibreWolf)
    ├── chromium-bookmarks-extraction(leaf — Chrome/Brave/Chromium/Edge/Vivaldi)
    └── safari-bookmarks-extraction  (leaf — macOS)
```

Leaves may not exist yet. Where a leaf is missing, report the browser as
unsupported and continue — never block the whole migration.

---

## Responsibilities (what THIS skill does)

1. **Detect browsers & profiles** on the source.
2. **Dispatch** to the correct extraction leaf per browser.
3. **Validate** each leaf's output against `FORMAT.md`.
4. **Package** all `bookmarks.json` files into the staging tree.
5. **Record** in the bundle manifest what was collected / skipped / unsupported.

What this skill does NOT do: read `places.sqlite` / `Bookmarks` JSON / Safari
plists itself. That is leaf mechanics.

---

## Step 1 — Detect browsers and profiles

Platform-aware. Identify each installed browser and ITS profiles.

### Linux
```sh
# install presence (native, AUR, flatpak)
pacman -Qq 2>/dev/null | grep -iE 'firefox|librewolf|chromium|google-chrome|brave|vivaldi|microsoft-edge'
pacman -Qmq 2>/dev/null | grep -iE 'browser|firefox|brave|vivaldi'
ls ~/.var/app 2>/dev/null   # flatpak browsers

# profile dirs
ls -d ~/.mozilla/firefox/*/ 2>/dev/null
ls -d ~/.librewolf/*/ 2>/dev/null
ls -d ~/.config/google-chrome/* ~/.config/chromium/* \
      ~/.config/BraveSoftware/Brave-Browser/* ~/.config/vivaldi/* \
      ~/.config/microsoft-edge/* 2>/dev/null
```
Firefox profiles: parse `~/.mozilla/firefox/profiles.ini` for the real list.
Chromium profiles: `Default`, `Profile 1`, `Profile 2`, …

### macOS
```sh
ls /Applications | grep -iE 'Firefox|LibreWolf|Chrome|Chromium|Brave|Vivaldi|Edge|Safari'
ls -d "$HOME/Library/Application Support/Firefox/Profiles/"*/ 2>/dev/null
ls -d "$HOME/Library/Application Support/Google/Chrome/"* \
      "$HOME/Library/Application Support/BraveSoftware/Brave-Browser/"* \
      "$HOME/Library/Application Support/Chromium/"* 2>/dev/null
# Safari bookmarks: ~/Library/Safari/Bookmarks.plist (Full Disk Access may be required)
```

Map each detected browser to a **canonical id** (`FORMAT.md`: `firefox`,
`librewolf`, `chrome`, `chromium`, `brave`, `edge`, `vivaldi`, `safari`) and the
extraction leaf name `<id>-bookmarks-extraction`.

Present the detected browsers/profiles to the user; confirm which to include.

---

## Step 2 — Dispatch to extraction leaves

For each included (browser, profile):

1. Determine the leaf skill name: `<browser-id>-bookmarks-extraction`.
2. If that skill is available, **load it** (via the `skill` tool) and follow its
   instructions, passing the profile path and the required output location:
   ```
   browsers/<host>/<browser>/<profile>/bookmarks.json
   ```
3. If the leaf is NOT available: record the browser under `unsupported` in the
   manifest and tell the user (they can contribute a leaf later). Do not guess at
   the browser's internal format yourself.

The leaf is responsible for producing valid url-groups output (folder grouping,
hierarchy preserved). You only tell it which profile and where to write.

---

## Step 3 — Validate leaf output

For each produced `bookmarks.json`, sanity-check against `FORMAT.md`:
- `format == "url-groups"`, `version` supported, `datatype == "bookmarks"`.
- Every group `state == "inactive"`, `container.type == "folder"` (hierarchy in
  `container.path`).
- `links[].url` present and `http(s)`; titles present (or URL fallback).

If a leaf emits malformed output, STOP and report — do not package broken data.

---

## Step 4 — Package & record

- Place all validated `bookmarks.json` files under the staging tree
  (`browsers/<host>/<browser>/<profile>/bookmarks.json`).
- Add manifest items (per the migration MANIFEST contract) with
  `category: "bookmarks"`, `merge: "union-dedup"`, `browser`, `profile`, and the
  staging path.
- Record any `unsupported`/`skipped` browsers in the manifest `manual` list.

The `user-migration-source` orchestrator handles the actual bundle packing and
delivery. Your output is the staged bookmarks files + manifest entries.

---

## Rules

- Never read a browser's files directly — always go through a leaf.
- Missing leaf → report unsupported, keep going. Never block migration.
- Bookmarks are URLs + titles + folder structure only. No secrets.
- Preserve folder hierarchy losslessly (leaves enforce; you validate).
- Be open-minded: if a leaf reports links it couldn't place in a folder, they
  arrive in a `flat-pool` group — accept and package them, don't drop them.

Base directory: file:///home/domovoy/.agents/skills/browser-bookmarks-source
`FORMAT.md` is relative to this base directory.
