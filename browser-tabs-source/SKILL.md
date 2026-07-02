---
name: browser-tabs-source
description: Collect open browser tabs from all browsers on a source machine into the shared url-groups format during a user migration. Detects browsers, ensures they are closed, dispatches to per-browser tab extraction leaf skills, and packages results grouped by window (or flat pool). Use on the SOURCE machine when migrating open tabs. Does not implement browser-specific extraction itself.
license: GPL-3.0-or-later
compatibility: opencode
metadata:
  family: user-migration
  tier: logic
  datatype: tabs
  direction: source
  leaf_pattern: <browser>-tabs-extraction
---

# browser-tabs-source

**Tier-1 logic skill.** You own the *open-tabs-collection logic* for a migration
SOURCE: detect browsers, ensure each is closed, dispatch to the matching
per-browser **tab extraction leaf**, and package every browser's open tabs into
the shared **url-groups** format (tabs profile, `state: "active"`).

Read the format contract first: `FORMAT.md` (tabs profile) and the canonical
envelope it references: `../browser-bookmarks-source/FORMAT.md`.

Invoked by `user-migration-source`. Logical hierarchy (flat dirs):

```
user-migration-source
└── browser-tabs-source              (this skill — logic + format)
    ├── firefox-tabs-extraction      (leaf; covers LibreWolf; per-window)
    ├── brave-tabs-extraction        (leaf; Chromium-family; flat-pool)
    └── safari-tabs-extraction       (leaf; macOS; per-window)
```

Leaves may not exist yet — report unsupported browsers and continue.

---

## What "don't lose tabs" means here (agreed decision)

We preserve **URLs** (with title + window grouping + order where available), NOT
native session state. This is the only model that survives cross-browser,
cross-platform routing (a Safari window can be routed into Brave on Linux). No
open tab's URL is lost; scroll/form/in-tab-history are not promised.

---

## Responsibilities

1. **Detect browsers & profiles** (same detection as bookmarks; see that skill).
2. **Ensure each browser is CLOSED** before extraction.
3. **Dispatch** to `<browser>-tabs-extraction` leaves.
4. **Validate** output against `FORMAT.md` (tabs profile).
5. **Package** `tabs.json` files + record manifest entries.

NOT this skill's job: parsing `recovery.jsonlz4` / SNSS / `LastSession.plist` —
that is leaf mechanics.

---

## Step 1 — Detect (see browser-bookmarks-source Step 1)

Reuse the same browser/profile detection. Map each to a canonical id and leaf
name `<id>-tabs-extraction`. Confirm inclusions with the user.

---

## Step 2 — Ensure browsers are CLOSED

Open tabs only flush to disk when the browser exits cleanly.

```sh
# Linux
pgrep -a -i 'firefox|librewolf|chrome|chromium|brave|vivaldi|edge'
# macOS
pgrep -il 'firefox|librewolf|Google Chrome|Chromium|Brave|Vivaldi|Safari'
```

If a target browser is running, STOP and ask the user to quit it fully (verify it
wrote `sessionstore.jsonlz4` / `Sessions/` on exit). Never kill it yourself —
ask. Then re-check before extracting.

---

## Step 3 — Dispatch to extraction leaves

For each included (browser, profile):
1. Leaf name: `<browser-id>-tabs-extraction`.
2. If available, load it and follow its instructions; output location:
   ```
   browsers/<host>/<browser>/<profile>/tabs.json
   ```
3. If unavailable, record `unsupported` and continue.

Grouping fidelity the leaf must honor (`FORMAT.md`):
- Firefox/LibreWolf, Safari → **per-window** groups.
- Chromium/Chrome/Brave/Edge/Vivaldi → **flat-pool** (one group).

---

## Step 4 — Validate output

Per `tabs.json`: `datatype == "tabs"`, every group `state == "active"`,
`container.type` is `window` (with `index`) or `flat-pool`, `links[].url` is
`http(s)`. Reject `about:`/`chrome://` unless the user opted to keep them.

Malformed → STOP and report.

---

## Step 5 — Package & record

- Stage `tabs.json` under `browsers/<host>/<browser>/<profile>/tabs.json`.
- Manifest items: `category: "tabs"`, `merge: "union-dedup"`, `browser`,
  `profile`, staging path.
- Unsupported/closed-browser issues → manifest `manual` list.

The orchestrator packs and delivers the bundle.

---

## Rules

- Browsers MUST be closed before extraction — verify, don't assume.
- Never read session files directly — go through a leaf.
- URLs only; no session secrets, no cookies.
- Preserve window grouping & tab order where the format supports it.
- Missing leaf → report, continue. Never block migration.

Base directory: file:///home/domovoy/.agents/skills/browser-tabs-source
`FORMAT.md` (and `../browser-bookmarks-source/FORMAT.md`) are relative to this base.
