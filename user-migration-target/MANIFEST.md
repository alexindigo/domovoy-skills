# Migration Bundle Contract (`manifest.json`)

Shared contract between `user-migration-source` (producer) and
`user-migration-target` (consumer). Both skills MUST agree on this schema. It is
deliberately **open-minded**: categories are open-ended, but the set of *merge
strategies* is fixed so the target can handle any item — including ones the
authors never anticipated.

Schema is **versioned** (`schema` field). Bump it on breaking changes; the target
must refuse a `schema` it doesn't understand and ask the user.

---

## Core principles (read first)

1. **Home is the root.** All in-home migrated content is stored **relative to the
   source account's home directory** (`rel_path`, e.g. `.ssh/config`,
   `.config/foo/bar`). The bundle contains NO absolute source paths for in-home
   content. The target reconstructs absolute paths under **its own** destination
   home. This makes usernames and home prefixes irrelevant for *placement*.

2. **Source identity ≠ target identity.** The human account name/uid/home on the
   source (e.g. `alex` / 501 / `/Users/alex` on macOS) may differ entirely from
   the target (e.g. `user` / 1000 / `/home/user`). The manifest records the
   **source** identity; the target resolves its **own** destination account
   (asking the human — never assuming `user` or matching the source).

3. **The bundle is inert payload.** The target does NOT honor, trust, or execute
   any absolute path found *inside* migrated files. It asks the human where
   payload goes, and for text files it may **examine contents and report** likely
   issues (e.g. an internal `/Users/alex/...` reference that won't exist on the
   target) for the human to resolve. There is **NO automatic content rewriting.**

4. **Accounts are scoped by the human.** Both source and target present the
   candidate human accounts; the human decides which are in/out of scope. Multi-
   account machines are supported.

5. **Out-of-home content is opt-in and separate.** Anything outside `$HOME` is
   only included if the human asks; it travels as a **separate archive** with
   absolute paths (a tar can't cleanly mix relative and absolute entries).

---

## Top-level structure

Example uses a **macOS** source to make source≠target obvious (source user `alex`,
home `/Users/alex`; a Linux target might integrate this as `user` / `/home/user`):

```json
{
  "schema": "1",
  "bundle": {
    "archive": "migration-bundle-macbook-2026-06-28T17-00-00.tar.gz",
    "format": "gzip",
    "root": "macbook-2026-06-28T17-00-00",
    "outside_home_archive": "outside-home.tar"
  },
  "source": {
    "host": "macbook",
    "os": "darwin",
    "account": "alex",
    "uid": 501,
    "home": "/Users/alex",
    "shell": "/bin/zsh"
  },
  "generated": "2026-06-28T17:00:00-07:00",
  "inventory": {
    "native":  [],
    "foreign": ["some-brew-formula"],
    "flatpak": [],
    "apps":    ["Brave Browser", "Vivaldi"]
  },
  "items": [ /* see below */ ],
  "manual": [
    "macos-keychain: Wi-Fi and app passwords must be re-entered by the user",
    "browser 'Vivaldi' present on source but not on target"
  ]
}
```

> The **target** identity is NOT in the manifest — it is resolved on the target
> machine (the human confirms which destination account to integrate into). The
> target maps `rel_path` under its own home; `source.home`/`source.uid` are used
> only for provenance and for *reporting* (not rewriting) embedded paths.

### `bundle`
| Field     | Meaning                                                        |
|-----------|---------------------------------------------------------------|
| `archive` | exact bundle filename as delivered                            |
| `format`  | `gzip` or `zstd` — target verifies it has the decompressor    |
| `root`    | top-level dir inside the archive (`<host>-<iso8601>`)         |
| `outside_home_archive` | (optional) filename of the SEPARATE archive holding opt-in out-of-home content with absolute paths |

> **Format compatibility:** `gzip` is the default — preinstalled and `tar`-native
> on macOS, Debian 12, and Arch. `zstd` is used only when BOTH ends had it
> (preinstalled only on Arch). The target MUST check `command -v` for the
> matching tool before unpacking and stop with a clear message if missing.

### `source`
Identity of the producing machine's **human account** whose data this bundle
carries (`host`, `os`, `account`, `uid`, `home`, `shell`). Recorded for
provenance and for *reporting* embedded absolute paths — NOT for automatic
rewriting. The source account name/uid/home may differ entirely from the
target's. If a machine has multiple in-scope human accounts, the source produces
one bundle (or one `source` section) per account.

### `inventory`
Informational app lists. The target **reports** the delta (source apps not present
on target) but NEVER auto-installs.

### `manual`
Free-text items that cannot be migrated automatically (macOS keychain, browsers
absent on target, etc.). Target surfaces these to the user.

---

## `items[]`

Each item describes one thing to migrate and HOW to merge it.

```json
{
  "category": "ssh",
  "path": "payload/.ssh",
  "rel_path": ".ssh",
  "merge": "append-dedup",
  "secret": true,
  "location": "home",
  "transport": "bundle",
  "size": "20K",
  "note": "optional human note"
}
```

| Field       | Required | Meaning                                                            |
|-------------|----------|-------------------------------------------------------------------|
| `category`  | yes      | OPEN vocabulary (see below). Unknown categories are allowed.       |
| `path`      | yes      | path INSIDE the bundle (relative to `bundle.root`) OR sidecar path |
| `rel_path`  | in-home  | destination path **relative to the destination account's home** (e.g. `.ssh`). Target prepends `<target-home>`. The great equalizer — no usernames/absolute prefixes. |
| `abs_path`  | out-of-home | absolute destination for `location: "outside-home"` items (lives in the separate out-of-home archive) |
| `location`  | yes      | `home` (default, home-relative) or `outside-home` (absolute, separate archive) |
| `merge`     | yes      | FIXED vocabulary (see below) — how the target integrates it        |
| `secret`    | no       | `true` → never log contents; preserve strict perms                 |
| `transport` | no       | `bundle` (default, inside tar) or `sidecar` (rsync'd beside bundle)|
| `browser`   | no       | for bookmarks/tabs: `firefox`/`chromium` + family name            |
| `profile`   | no       | browser profile name                                              |
| `size`      | no       | informational                                                     |
| `note`      | no       | human-readable context                                            |

> The target places in-home items at `<target-home>/<rel_path>` — where
> `<target-home>` is the human-confirmed destination account's home, NOT assumed
> to be `/home/user`. It NEVER uses `source.home` as a destination. Ownership is
> set to the destination account (`<target-user>:<target-group>`), never the
> source's numeric uid.

### `category` — OPEN vocabulary
Known values: `ssh`, `gpg`, `shell`, `gitconfig`, `dotconfig`, `appdata`,
`bookmarks`, `tabs`, `dir`, `userdirs`, `skip`, `unknown`.

The list is NOT closed. A source MAY emit any category string. The target routes
purely on `merge`, so an unrecognized `category` still integrates correctly. For
genuinely unclassified items the source SHOULD use `unknown` + a conservative
`merge` (usually `copy-if-absent`).

### `merge` — FIXED vocabulary
The target MUST implement exactly these strategies:

| Strategy         | Target behaviour                                                                 |
|------------------|---------------------------------------------------------------------------------|
| `append-dedup`   | append lines not already present (e.g. `authorized_keys`, `known_hosts`)         |
| `union-dedup`    | merge collections, dedup by natural key (bookmarks/tabs by URL)                  |
| `copy-if-absent` | copy only if destination does not already exist; never overwrite                 |
| `rsync`          | `rsync` merge into dest (opt-in large dirs); never `--delete`                     |
| `review-diff`    | show a diff to the user, integrate interactively; never blind-overwrite          |
| `skip`           | do nothing; informational only (e.g. `reason: syncthing-managed`)                |

A `skip` item SHOULD carry a `reason`.

---

## Hard invariants (both skills enforce)

1. **One-way.** Target never deletes or overwrites source-side data, and never
   `--delete`s on its own existing data.
2. **Pre-existing wins unless reviewed.** Anything already on the target is
   preserved; conflicts go through `review-diff` or `copy-if-absent`.
3. **Secrets never logged.** Items with `secret: true` have perms preserved and
   contents kept out of all output/logs/reports.
4. **Bookmarks/tabs are additive.** Always union+dedup; also emit dated
   "Migrated from <host>" / "Recovered tabs — <host> <date>" folders so nothing
   is silently lost.
5. **Home is the root; the target owns placement.** In-home items are placed at
   `<target-home>/<rel_path>` under the human-confirmed destination account.
   Ownership → destination account (`<target-user>:<target-group>`), never the
   source's numeric UID (no `rsync --numeric-ids`). The target NEVER treats
   `source.home` as a real path on this machine.
6. **Inert payload — no content rewriting.** The target does not honor or rewrite
   absolute paths found *inside* migrated files. For text files it MAY examine
   contents and **report** likely issues (e.g. embedded `source.home` references)
   for the human to resolve. No silent substitution.
7. **Unknown is safe.** Unrecognized `category` integrates via its `merge`;
   when in doubt the source uses `copy-if-absent`.
