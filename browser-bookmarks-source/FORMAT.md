# URL-Group Interchange Format — Canonical Envelope (v1)

This is the **shared contract** that every browser provider (extraction leaf) and
every consumer (injection leaf / sink) conforms to. Bookmarks and open tabs are
BOTH expressed as "URL-groups" using ONE envelope with two *profiles*:

- **bookmarks profile** — `state: "inactive"`, grouped by **folder**
- **tabs profile** — `state: "active"`, grouped by **window** or **flat-pool**

The tabs profile is documented in `../browser-tabs-source/FORMAT.md`; it uses this
same envelope. A consumer routes purely on the envelope and never needs to know
which browser or datatype produced a group — that is what makes browsers,
Linkwarden, and plain lists interchangeable destinations.

> **Why one envelope?** The user's mental model: a bookmark is just an *inactive*
> URL and an open tab is an *active* URL. Both are URLs looking for a home. One
> format lets the target route any group to any sink uniformly.

---

## File

Each provider writes ONE JSON file per (browser, profile, datatype) into the
bundle's staging tree:

```
browsers/<host>/<browser>/<profile>/bookmarks.json
browsers/<host>/<browser>/<profile>/tabs.json
```

Encoding: UTF-8, JSON. No secrets ever appear in these files (URLs/titles only).

---

## Envelope schema

```json
{
  "format": "url-groups",
  "version": "1",
  "datatype": "bookmarks",          // "bookmarks" | "tabs"
  "origin": {
    "host": "arch-laptop",
    "os": "linux",                  // "linux" | "darwin"
    "browser": "firefox",           // canonical family/brand id (see below)
    "browser_version": "126.0",     // best-effort; "" if unknown
    "profile": "default-release"     // profile name/id as the browser knows it
  },
  "generated": "2026-06-29T12:00:00-07:00",
  "groups": [ /* see Group */ ]
}
```

### Group

```json
{
  "id": "w1",                       // unique within this file
  "state": "inactive",              // "active" (tabs) | "inactive" (bookmarks)
  "container": {
    "type": "folder",               // "folder" | "window" | "flat-pool"
    "path": ["Bookmarks Bar", "Dev"],   // folder hierarchy (folder type)
    "index": 1,                     // window number (window type)
    "title_hint": "Dev"             // human label to recognize the group
  },
  "links": [
    {
      "url": "https://example.com/",
      "title": "Example",
      "active_tab": false,          // tabs only: is this the focused tab?
      "pinned": false,              // optional, best-effort
      "added": "2026-01-02T00:00:00Z"  // optional (bookmarks); "" if unknown
    }
  ]
}
```

---

## Field rules

| Field | Required | Notes |
|-------|----------|-------|
| `format` | yes | always `"url-groups"` |
| `version` | yes | bump on breaking change; consumer refuses unknown major |
| `datatype` | yes | `bookmarks` or `tabs` |
| `origin.*` | yes | provenance; drives dedup tagging + routing labels |
| `groups[].id` | yes | unique within file |
| `groups[].state` | yes | `inactive` for bookmarks, `active` for tabs |
| `container.type` | yes | `folder` (bookmarks), `window`/`flat-pool` (tabs) |
| `container.path` | folder only | array preserves hierarchy losslessly |
| `container.index` | window only | source window number |
| `container.title_hint` | recommended | so the user can recognize a group when routing |
| `links[].url` | yes | absolute URL; non-`http(s)` schemes (`about:`, `chrome:`) SHOULD be dropped or flagged |
| `links[].title` | yes | falls back to URL if the browser has none |
| `links[].active_tab` | tabs only | exactly one `true` per window group if known |

---

## Grouping fidelity (agreed per browser)

| Browser family | bookmarks (inactive) | tabs (active) |
|----------------|----------------------|---------------|
| Firefox / LibreWolf | per **folder** (hierarchy) | per **window** |
| Safari | per **folder** | per **window** |
| Chromium / Chrome / Brave / Edge / Vivaldi | per **folder** | **flat-pool** (one group; SNSS window reconstruction is unreliable — accepted) |

A `flat-pool` group has `container.type: "flat-pool"` and no `index`.

---

## Canonical browser ids (`origin.browser`)

Use these stable ids so leaves and consumers agree:

`firefox`, `librewolf`, `chrome`, `chromium`, `brave`, `edge`, `vivaldi`,
`safari`. Firefox-family share Firefox mechanics; Chromium-family share Chromium
mechanics. A new browser adds a new id + its own leaves.

---

## Hard rules

1. **Lossless grouping.** Folder hierarchy (`container.path`) and window grouping
   are preserved exactly as the source has them, within the fidelity table above.
2. **HTML/JSON safety.** Producers emit JSON (escaping handled by the JSON
   encoder). Consumers that render HTML (e.g. Netscape bookmark import) MUST
   HTML-escape `title`/`url`.
3. **No secrets.** Only URLs/titles/metadata — never cookies, tokens, passwords.
4. **Additive on the target.** Consumers MUST merge, never clobber existing data
   (see the target logic skills).
5. **Unknown is preserved.** A producer that finds links it cannot classify into
   a known container still emits them in a `flat-pool` group rather than dropping
   them.

---

## Leaf contract (for future extraction/injection skills)

- An **extraction leaf** (`<browser>-<datatype>-extraction`) reads ONE browser and
  emits one or more files in this format. It MUST conform to this schema and the
  fidelity table.
- An **injection leaf** (`<browser>-<datatype>-injection`) consumes this format
  and writes into ONE browser, additively.
- A **sink** (e.g. `linkwarden-bookmarks-target`) consumes this format into a
  non-browser endpoint.

Leaves depend ONLY on this document — they need no knowledge of the orchestrators
or other browsers.
