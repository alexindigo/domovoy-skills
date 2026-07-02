# URL-Group Interchange Format — Tabs Profile (v1)

Open tabs use the **same envelope** as bookmarks. The canonical envelope schema
lives in `../browser-bookmarks-source/FORMAT.md` — read it first. This file only
documents what is SPECIFIC to the tabs profile.

---

## Tabs profile = `state: "active"`

```json
{
  "format": "url-groups",
  "version": "1",
  "datatype": "tabs",
  "origin": { "host": "...", "os": "...", "browser": "...", "browser_version": "...", "profile": "..." },
  "generated": "...",
  "groups": [
    {
      "id": "w1",
      "state": "active",
      "container": { "type": "window", "index": 1, "title_hint": "GitHub — work" },
      "links": [
        { "url": "https://github.com/...", "title": "...", "active_tab": true, "pinned": true },
        { "url": "https://...",            "title": "...", "active_tab": false }
      ]
    }
  ]
}
```

---

## Grouping (the key tabs decision)

| Browser family | Tabs grouping | Mechanism |
|----------------|---------------|-----------|
| Firefox / LibreWolf | **per window** | `sessionstore.jsonlz4` / `recovery.jsonlz4` has native `windows[].tabs[]` |
| Safari | **per window** | `LastSession.plist` → `SessionWindows[].TabStates[]` (or `SafariTabs.db` on Safari 15+) |
| Chromium / Chrome / Brave / Edge / Vivaldi | **flat-pool** | SNSS window reconstruction is unreliable → one group of all open tabs (deduped) |

- **window** group: `container.type: "window"`, `container.index: <N>`. Preserve
  tab order; flag the focused tab with `active_tab: true` when known.
- **flat-pool** group: `container.type: "flat-pool"`, no `index`. All open tabs of
  the profile as one deduped group. `active_tab` may be omitted.

---

## Extraction notes (for future tabs leaves)

- **Browser MUST be closed** before extraction, or live session state is not
  flushed to disk. The provider/orchestrator verifies this.
- **URLs only** — we preserve the URL (and title/order where available), NOT live
  session state (scroll position, form data, in-tab history). This is the agreed
  "URL preservation" level: no open tab is lost, but native session fidelity is
  not promised. This is the only model that survives cross-browser, cross-platform
  routing (e.g. Safari tabs → Brave).
- Drop non-`http(s)` URLs (`about:`, `chrome://`, `file:` may be flagged but
  default-dropped) unless the user asks to keep them.
- macOS sources may require **Full Disk Access** for the extracting tool to read
  Safari's container — the Safari leaf documents this.

---

## Routing (target side)

Each tabs group is routed independently by the user on the target to a
destination (a browser via injection leaf, or a sink like Linkwarden / plain
list). See `../browser-tabs-target/SKILL.md`. A `flat-pool` group routes as a
single unit; `window` groups can each go to different destinations.
