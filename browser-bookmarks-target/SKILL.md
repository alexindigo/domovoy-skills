---
name: browser-bookmarks-target
description: Integrate bookmarks from migration bundles into a target machine. Unpacks the shared url-groups format from one or more sources, merges and deduplicates them without losing existing bookmarks, and routes each group to a destination (a browser via injection leaf, or a sink like Linkwarden or a plain list) with user guidance. Use on the TARGET machine when migrating bookmarks.
license: GPL-3.0-or-later
compatibility: opencode
metadata:
  family: user-migration
  tier: logic
  datatype: bookmarks
  direction: target
  leaf_pattern: <browser>-bookmarks-injection
  sink_pattern: <endpoint>-bookmarks-target
---

# browser-bookmarks-target

**Tier-1 logic skill.** You own the *bookmarks-integration logic* on a migration
TARGET: read the shared **url-groups** bookmark data from one or more bundles,
**merge and dedup** without losing anything, and **route** each group to a
destination chosen by the user — a browser (via an injection leaf) or a non-
browser sink (Linkwarden, plain list). You do NOT write any browser's files
directly — that is the injection leaf's job.

Read the format contract first: `../browser-bookmarks-source/FORMAT.md`.

Invoked by `user-migration-target`. Logical hierarchy (flat dirs):

```
user-migration-target
└── browser-bookmarks-target          (this skill — merge + routing logic)
    ├── firefox-bookmarks-injection   (leaf; covers LibreWolf)
    ├── brave-bookmarks-injection     (leaf; Chromium-family)
    └── linkwarden-bookmarks-target    (sink — non-browser consumer of same format)
```

Leaves/sinks may not exist yet — where a chosen destination has no
injection/sink skill, fall back to emitting a portable file (Netscape HTML) for
the user to import manually. Never lose data.

---

## Responsibilities

1. **Collect** every `bookmarks.json` from every unpacked bundle.
2. **Merge & dedup** across all sources + the target's existing bookmarks.
3. **Present groups** to the user and take routing decisions.
4. **Dispatch** each routed group to an injection leaf or sink.
5. **Verify** nothing was lost; report.

NOT this skill's job: editing `places.sqlite` / `Bookmarks` JSON — that is leaf
mechanics.

---

## Step 1 — Collect

Gather all `bookmarks.json` across bundles:
```
~/migrations/work/<bundle-root>/browsers/<host>/<browser>/<profile>/bookmarks.json
```
Validate each against the format (`format/version/datatype`). Refuse unknown
major `version` and ask the user.

---

## Step 2 — Merge & dedup (never lose)

Build a working set of all groups from all sources. Dedup policy:
- **Key links by normalized URL** (lowercase scheme/host, strip trailing slash,
  drop fragments only if the user agrees; default keep fragments).
- When the same URL appears in multiple sources, keep one link but **retain the
  richest title** and note all origins.
- **Preserve folder structure** (`container.path`) as the grouping. Do NOT flatten.
- ALWAYS keep, in addition to any merged view, a dated **"Migrated from <host>"**
  folder per source so the user can see exactly what came from where. Nothing is
  silently merged away.

This is additive: the target's EXISTING bookmarks are never deleted or
overwritten — migrated bookmarks are added alongside.

---

## Step 3 — Route groups (with the user)

Present the groups (folder, source, count, title hint). For each group (or batch),
the user picks a destination:

| Destination | How it's handled |
|-------------|------------------|
| A browser here (`firefox`/`librewolf`/`brave`/…) | dispatch to `<browser>-bookmarks-injection` |
| Linkwarden | dispatch to `linkwarden-bookmarks-target` sink |
| Plain list / HTML | emit Netscape HTML (`sink` fallback) for manual import |

The user may send different folders to different destinations, or everything to
one. Routing is interactive — no automatic destination guessing beyond sensible
defaults you may suggest (e.g. a Firefox source folder → LibreWolf).

---

## Step 4 — Dispatch to injection leaf / sink

For each routed group:
1. Determine the destination skill:
   - browser → `<browser-id>-bookmarks-injection`
   - sink → `<endpoint>-bookmarks-target` (e.g. `linkwarden-bookmarks-target`)
2. If available, load it and pass the group(s) + destination profile.
3. If unavailable, FALL BACK: emit a Netscape-format HTML file
   (`~/migrations/work/bookmarks-out/<dest>-<host>-<date>.html`) and tell the user
   to import it manually. HTML-escape `title`/`url`.

Injection leaves MUST be additive (import, not replace). This skill enforces that
contract; it does not itself touch browser files.

---

## Step 5 — Verify & report

- Confirm total integrated link count ≥ union of all sources (after dedup), i.e.
  nothing lost.
- For browser destinations, confirm the injection leaf reported success and the
  browser's existing bookmarks are intact.
- Report: per source → routed where, dedup count, any fallback HTML emitted, any
  destinations with no leaf (manual import needed).

---

## Sink interface (for non-browser destinations)

A **sink** consuming this format is named `<endpoint>-bookmarks-target` and must:
- Accept url-groups (folders + links) for a chosen subset of groups.
- Map a group → its own container concept (e.g. Linkwarden collection; tags from
  `origin`).
- Be additive / idempotent where possible (don't duplicate on re-run).
- Handle its own auth as a **secret** (never logged).

`linkwarden-bookmarks-target` is the reference sink (deferred). Until it exists,
the HTML fallback (Step 4) covers non-browser needs.

---

## Rules

- Never delete or overwrite the target's existing bookmarks.
- Always keep dated "Migrated from <host>" folders — nothing silently lost.
- Never edit browser files directly — go through injection leaves.
- Missing leaf/sink → HTML fallback, never block.
- Bookmarks are URLs/titles/folders only. No secrets.

Base directory: file:///home/domovoy/.agents/skills/browser-bookmarks-target
`../browser-bookmarks-source/FORMAT.md` is the format contract.
