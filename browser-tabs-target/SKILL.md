---
name: browser-tabs-target
description: Integrate open browser tabs from migration bundles into a target machine. Unpacks the shared url-groups tabs format from one or more sources, lets the user route each tab group (window or flat pool) to a destination browser or sink, and dispatches to per-browser injection leaf skills. Preserves tab URLs so none are lost. Use on the TARGET machine when migrating open tabs.
license: GPL-3.0-or-later
compatibility: opencode
metadata:
  family: user-migration
  tier: logic
  datatype: tabs
  direction: target
  leaf_pattern: <browser>-tabs-injection
  sink_pattern: <endpoint>-tabs-target
---

# browser-tabs-target

**Tier-1 logic skill.** You own the *open-tabs-integration logic* on a migration
TARGET: read the shared **url-groups** tabs data from one or more bundles, let the
user **route** each tab group (a window, or a flat-pool) to a destination, and
dispatch to the matching per-browser **tab injection leaf** (or a sink). You do
NOT write browser files directly.

Read the format contract first: `../browser-tabs-source/FORMAT.md` and the
canonical envelope `../browser-bookmarks-source/FORMAT.md`.

Invoked by `user-migration-target`. Logical hierarchy (flat dirs):

```
user-migration-target
└── browser-tabs-target               (this skill — routing logic)
    ├── firefox-tabs-injection        (leaf; covers LibreWolf)
    ├── brave-tabs-injection          (leaf; Chromium-family; Preferences restore)
    └── <endpoint>-tabs-target         (sink; e.g. Linkwarden / plain list)
```

Leaves/sinks may not exist yet — fall back to a "recovered tabs" file the user
opens manually. Never lose a tab URL.

---

## Model (agreed)

Tabs are routed as **groups**: a Firefox/Safari **window** is one group; a
Chromium/Brave profile is one **flat-pool** group. The user assigns each group to
a destination independently — regardless of which browser it came from (a Safari
window can go into Brave). We preserve URLs (+ order/grouping), not native session
state.

---

## Responsibilities

1. **Collect** every `tabs.json` from every bundle.
2. **Present groups** with provenance so the user can route them.
3. **Route** each group → a destination browser or sink.
4. **Dispatch** to injection leaf / sink (dedup within a destination).
5. **Verify** no tab URL lost; report.

NOT this skill's job: writing `Preferences`/session files — leaf mechanics.

---

## Step 1 — Collect

Gather all `tabs.json`:
```
~/migrations/work/<bundle-root>/browsers/<host>/<browser>/<profile>/tabs.json
```
Validate format/version/datatype. Build the flat list of all groups across all
sources, each labeled `origin{host,browser,profile}` + `container` (window index
or flat-pool) + count + `title_hint`.

---

## Step 2 — Present groups for routing (with the user)

Show the user the full pool of tab-groups, e.g.:
```
[1] mac / safari   window 1   (8 tabs)   "News"
[2] mac / brave    flat-pool  (23 tabs)  "Brave (Mac)"
[3] arch / firefox window 1   (5 tabs)   "Docs"
[4] arch / brave   flat-pool  (40 tabs)  "Brave (Arch)"
```
The user assigns each group → a destination. They may merge several groups into
one destination, split, or drop some. No automatic routing — you may *suggest*
defaults but the user decides.

---

## Step 3 — Route & dispatch

For each routed group → destination:
1. Destination skill:
   - browser → `<browser-id>-tabs-injection`
   - sink → `<endpoint>-tabs-target`
2. If available, load it; pass the group(s) + destination profile. Dedup link URLs
   within the same destination bucket (e.g. two Brave pools merged into target
   Brave → one deduped set).
3. If unavailable, FALL BACK: emit a dated **"Recovered tabs — <host> <date>"**
   file (plain URL list + an HTML page with clickable links) under
   `~/migrations/work/tabs-out/` and tell the user to open it. HTML-escape output.

### Per-destination mechanism (informational; leaves implement)
- **Chromium/Brave injection** → write `Preferences` `session.restore_on_startup`
  + `session.startup_urls` (browser closed) — opens the URLs on next launch,
  additive to existing startup URLs.
- **Firefox/LibreWolf injection** → open URLs as a recovered window / synthesized
  session, non-clobbering of any existing session.

---

## Step 4 — Verify & report

- Confirm every routed group's URLs reached a destination or a fallback file (no
  silent loss).
- Report: each group → destination, dedup counts, any fallback files, any
  destination lacking a leaf (manual open needed).
- Note that injected tabs appear on next browser launch (Chromium) or via the
  recovered window (Firefox).

---

## Sink interface (non-browser destinations)

A sink is `<endpoint>-tabs-target` and must accept url-groups, map them to its own
container, be additive/idempotent, and treat auth as a secret. Reference sink:
`linkwarden-tabs-target` (deferred — tabs become links in a collection).

---

## Rules

- Never lose a tab URL — fallback file if no leaf/sink.
- Never write browser files directly — go through injection leaves.
- Browsers should be closed during injection (leaves enforce).
- URLs only; no session secrets.
- Routing is interactive and per-group; user decides destinations.

Base directory: file:///home/domovoy/.agents/skills/browser-tabs-target
Format contracts: `../browser-tabs-source/FORMAT.md`,
`../browser-bookmarks-source/FORMAT.md`.
