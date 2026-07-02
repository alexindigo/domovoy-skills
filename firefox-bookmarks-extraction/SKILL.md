---
name: firefox-bookmarks-extraction
description: Extract bookmarks from a Firefox or LibreWolf profile into the shared url-groups format, preserving folder hierarchy. A leaf skill called by browser-bookmarks-source during a user migration. Reads places.sqlite read-only (via a temp copy) and emits a conforming bookmarks.json.
license: GPL-3.0-or-later
compatibility: opencode
metadata:
  family: user-migration
  tier: leaf
  parent: browser-bookmarks-source
  browser: firefox
  datatype: bookmarks
  action: extraction
---

# firefox-bookmarks-extraction

**Tier-2 leaf skill.** Mechanics for extracting **Firefox / LibreWolf** bookmarks
into the shared **url-groups** format. Called by `browser-bookmarks-source`. You
depend ONLY on the format contract: `../browser-bookmarks-source/FORMAT.md`.

Covers both **Firefox** and **LibreWolf** (identical `places.sqlite` schema; only
the profile root differs).

---

## What it produces

One `bookmarks.json` per profile, in url-groups format:
- `datatype: "bookmarks"`, each group `state: "inactive"`.
- One group **per bookmark folder**, with full hierarchy in `container.path`.
- **Empty folders dropped** (only folders containing links are emitted).
- Non-`http(s)` URLs dropped (`place:`, `javascript:`, `about:`…).

Runtime: **Python 3 stdlib** (`sqlite3` + `json`) — portable on Arch/Debian/macOS,
no dependencies. (Language is per-leaf; this one is naturally Python.)

---

## Profile locations

| OS | Firefox | LibreWolf |
|----|---------|-----------|
| Linux | `~/.mozilla/firefox/<profile>/` | `~/.librewolf/<profile>/` |
| Linux (flatpak) | `~/.var/app/org.mozilla.firefox/.mozilla/firefox/<profile>/` | `~/.var/app/io.gitlab.librewolf-community/.librewolf/<profile>/` |
| macOS | `~/Library/Application Support/Firefox/Profiles/<profile>/` | `~/Library/Application Support/LibreWolf/Profiles/<profile>/` |

Enumerate real profiles from `profiles.ini` in the Firefox/LibreWolf root
(`[Profile*]` sections, `Path=` + `IsRelative=`). `browser-bookmarks-source`
passes you the chosen profile dir.

---

## Run

```sh
python3 extract.py \
  --profile <profile_dir> \
  --out browsers/<host>/<browser>/<profile>/bookmarks.json \
  --host <host> --os <linux|darwin> \
  --browser <firefox|librewolf> \
  --profile-name <profile_name>
```

The script:
1. Copies `places.sqlite` to a temp file (never opens the live/locked DB).
2. Walks `moz_bookmarks` (`type 2` = folder, `type 1` = bookmark), building each
   bookmark's ancestor folder chain into `container.path`. Root folders are
   relabeled (Bookmarks Menu / Bookmarks Toolbar / Other Bookmarks / Mobile).
3. Emits one folder-group per non-empty folder; dedup happens later on the target.

---

## Rules

- Read-only on the profile — always operate on the temp copy.
- Preserve folder hierarchy losslessly; drop only empty folders.
- URLs/titles/dateAdded only — never any secret.
- If `places.sqlite` is missing, exit non-zero and report; do not fabricate data.

Base directory: file:///home/domovoy/.agents/skills/firefox-bookmarks-extraction
Format contract: `../browser-bookmarks-source/FORMAT.md`.
