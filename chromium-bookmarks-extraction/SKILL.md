---
name: chromium-bookmarks-extraction
description: Extract bookmarks from a Chromium-family browser profile (Chrome, Chromium, Brave, Edge, Vivaldi) into the shared url-groups format, preserving folder hierarchy. A leaf skill called by browser-bookmarks-source during a user migration. Reads the Bookmarks JSON file read-only and emits a conforming bookmarks.json.
license: GPL-3.0-or-later
compatibility: opencode
metadata:
  family: user-migration
  tier: leaf
  parent: browser-bookmarks-source
  browser: chromium
  datatype: bookmarks
  action: extraction
---

# chromium-bookmarks-extraction

**Tier-2 leaf skill.** Mechanics for extracting **Chromium-family** bookmarks into
the shared **url-groups** format. Called by `browser-bookmarks-source`. Depends
ONLY on the format contract: `../browser-bookmarks-source/FORMAT.md`.

Covers **Chrome, Chromium, Brave, Edge, Vivaldi** — they all store bookmarks in
the same plain-JSON `Bookmarks` file. The caller passes the specific browser id so
`origin.browser` is recorded correctly.

---

## What it produces

One `bookmarks.json` per profile, in url-groups format:
- `datatype: "bookmarks"`, each group `state: "inactive"`.
- One group **per bookmark folder**, full hierarchy in `container.path`
  (roots relabeled: Bookmark Bar / Other Bookmarks / Mobile Bookmarks).
- **Empty folders dropped.** Non-`http(s)` URLs dropped.

Runtime: **Python 3 stdlib** (`json`) — portable, no dependencies.

---

## Profile locations

| Browser | Linux | macOS |
|---------|-------|-------|
| Chrome | `~/.config/google-chrome/<Profile>/` | `~/Library/Application Support/Google/Chrome/<Profile>/` |
| Chromium | `~/.config/chromium/<Profile>/` | `~/Library/Application Support/Chromium/<Profile>/` |
| Brave | `~/.config/BraveSoftware/Brave-Browser/<Profile>/` | `~/Library/Application Support/BraveSoftware/Brave-Browser/<Profile>/` |
| Edge | `~/.config/microsoft-edge/<Profile>/` | `~/Library/Application Support/Microsoft Edge/<Profile>/` |
| Vivaldi | `~/.config/vivaldi/<Profile>/` | `~/Library/Application Support/Vivaldi/<Profile>/` |

`<Profile>` is `Default`, `Profile 1`, `Profile 2`, … Human profile names live in
the `User Data` root's `Local State` JSON (`profile.info_cache`). Flatpak variants
live under `~/.var/app/<app-id>/config/...`. `browser-bookmarks-source` passes you
the chosen profile dir + browser id.

---

## Run

```sh
python3 extract.py \
  --profile <profile_dir> \
  --out browsers/<host>/<browser>/<profile>/bookmarks.json \
  --host <host> --os <linux|darwin> \
  --browser <chrome|chromium|brave|edge|vivaldi> \
  --profile-name <profile_name>
```

The script copies the `Bookmarks` file to a temp path, parses the JSON tree
(`roots.{bookmark_bar,other,synced}` → recurse `children[]`), and emits one
folder-group per non-empty folder. Dedup happens later on the target.

---

## Rules

- Read-only on the profile — operate on the temp copy of `Bookmarks`.
- Preserve folder hierarchy; drop only empty folders.
- URLs/titles/date_added only — never any secret (no cookies, no `Login Data`).
- Set `origin.browser` to the specific brand the caller passed.
- If `Bookmarks` is missing/corrupt, exit non-zero and report; never fabricate.

Base directory: file:///home/domovoy/.agents/skills/chromium-bookmarks-extraction
Format contract: `../browser-bookmarks-source/FORMAT.md`.
