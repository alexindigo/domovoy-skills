---
name: user-migration-target
description: Orchestrate the TARGET side of a one-way user-data migration. Finds migration bundles dropped into this machine, verifies and unpacks them, and integrates their contents into the human user's environment, driving per-datatype target skills (bookmarks, tabs, and more) to merge and route data without losing anything. Use on the machine you are migrating TO.
license: GPL-3.0-or-later
compatibility: opencode
metadata:
  family: user-migration
  tier: orchestrator
  direction: target
---

# Skill: user-migration-target

You are running as the **TARGET** in a user-data migration. Your job: **find**
migration bundles dropped into this machine's incoming directory, **verify** and
**unpack** them, and **integrate** their contents into the human user's
environment here — working WITH the user to resolve conflicts and questionable
items. Multiple bundles from different sources may be present; merge them all
without any source clobbering another or the target's existing data.

This skill pairs with `user-migration-source`. They communicate through a single
artifact — a `.tar.gz` (or `.tar.zst`) **migration bundle** containing a
versioned `manifest.json`.

Read the shared contract before doing anything: `./MANIFEST.md`.

---

## Mental model

```
SOURCE (user-migration-source)              TARGET (this skill)
──────────────────────────────             ───────────────────
 packs bundle + manifest.json   ──────►  ~/migrations/incoming/  (domovoy home)
                                          1. scan for bundles (maybe many)
                                          2. verify checksums, check format
                                          3. unpack
                                          4. integrate per manifest (WITH user)
                                          5. verify result
                                          6. report + archive bundle (backup)
```

Bundles arrive under the **`domovoy` user's home** (`~/migrations/incoming/`),
because domovoy-to-domovoy SSH can write there (both ends are `domovoy`). The
human's data lives in a human account's home — you write there via `sudo` and fix
ownership to that account.

---

## Core model (read `MANIFEST.md` first)

- **Home is the root.** In-home items are stored home-relative (`rel_path`). You
  reconstruct absolute paths under **`<target-home>`** — the destination account's
  home on THIS machine. Never use `source.home` as a real path here.
- **Source identity ≠ target identity.** The source account (e.g. `mac-user` /
  `/Users/mac-user`) may differ from the destination (e.g. `user` / `/home/user`).
  You **resolve the destination account by asking the human** (Step 0) — never
  assume `user` or match the source.
- **The bundle is inert payload.** You do not honor or rewrite absolute paths
  inside migrated files. For text files you MAY examine and **report** likely
  issues (e.g. an embedded `source.home` reference) for the human to resolve.

Throughout, `<target-user>` / `<target-home>` are the human-confirmed destination
account resolved in Step 0.

---

## Golden rules

1. **Never delete or overwrite the human's existing data.** Pre-existing files
   win unless the user reviews a diff. Everything is additive/merge.
2. **Work WITH the user on conflicts.** `review-diff` items, browser-not-present,
   unknown categories — present, recommend, let the user decide. NO SURPRISES.
3. **Secrets never logged.** Items marked `secret` keep strict perms; contents
   never appear in output/logs/reports.
4. **Fix ownership.** Anything written into `<target-home>` must end up
   `<target-user>:<target-group>`. Files created via `sudo` default to
   `root:root` — always `sudo chown -R <target-user>:<target-group>` after.
5. **Home-relative placement; inert payload.** Place in-home items at
   `<target-home>/<rel_path>`; never trust source numeric UIDs; never rewrite
   file contents — examine and report instead.
6. **Keep the bundle as a backup** until the user decides its fate.

---

## Step 0 — Resolve the destination account(s) (ask the human)

Before touching any bundle, establish WHERE data will be integrated. The
destination is a **human account** on this machine — NOT `domovoy`, NOT `root`,
and NOT assumed to be `user` or to match the source.

List candidate human accounts and ask the human which are in scope:
```sh
# human accounts: real login shell, home under /home, uid >= 1000, not domovoy
getent passwd | awk -F: '$3>=1000 && $7!~/nologin|false/ && $1!="domovoy" {print $1"  uid="$3"  home="$6}'
```
- Present the list; the human confirms which account(s) are migration
  destinations (supports multiple / multi-account machines).
- For each chosen account resolve and remember:
  ```sh
  target_user=<chosen>
  target_home=$(getent passwd "$target_user" | cut -d: -f6)
  target_group=$(id -gn "$target_user")
  ```
- If a bundle carries data for one source account and there are multiple
  destinations, ask which destination it maps to. Record the mapping.

All later `<target-user>` / `<target-home>` / `<target-group>` refer to these
resolved values.

---

## Step 1 — Scan for bundles

```sh
ls -la ~/migrations/incoming/
```
List every `migration-bundle-*.tar.*` found. There may be several (e.g. one from
the Arch laptop, one from the MacBook, one from a USB-stick install). Process
them **one at a time**, but accumulate bookmarks/tabs across ALL of them before
the final browser merge (so dedup spans every source).

If the dir is empty, tell the user where to drop bundles and how the source
delivers them (rsync to `domovoy@<thishost>:~/migrations/incoming/`, USB, or
across a dual-boot reboot).

---

## Step 2 — Verify & check format (per bundle)

Read the manifest WITHOUT fully extracting first:
```sh
# gzip:
tar -xzf <bundle>.tar.gz --to-stdout '*/manifest.json' 2>/dev/null
# zstd:
tar --zstd -xf <bundle>.tar.zst --to-stdout '*/manifest.json' 2>/dev/null
```

From `manifest.json`:
- Check `schema` — if unknown, STOP and ask the user.
- Check `bundle.format` — verify the decompressor exists:
  ```sh
  case "$fmt" in
    gzip) command -v gzip >/dev/null || echo "MISSING gzip" ;;
    zstd) command -v zstd >/dev/null || echo "MISSING zstd — install zstd or ask source to repack as gzip" ;;
  esac
  ```
  `gzip` is universal; `zstd` may be absent (it's preinstalled only on Arch). If
  missing, STOP and tell the user (install `zstd`, or have the source repack with
  gzip). Do NOT half-unpack.

---

## Step 3 — Unpack

Unpack into a working dir under the domovoy's home (NOT yet into `<target-home>`):
```sh
mkdir -p ~/migrations/work/
# gzip:
tar -xzf ~/migrations/incoming/<bundle>.tar.gz -C ~/migrations/work/
# zstd:
tar --zstd -xf ~/migrations/incoming/<bundle>.tar.zst -C ~/migrations/work/
```

Verify checksums:
```sh
cd ~/migrations/work/<bundle.root>/
sha256sum -c checksums.sha256        # (shasum -a 256 -c on macOS targets)
```
Any mismatch → STOP, report to user (possible corruption / truncated transfer).

---

## Step 4 — Integrate (per manifest, WITH the user)

Iterate `items[]`. Route on the `merge` strategy (NOT on `category`, so unknown
categories still work). For each **in-home** item the real destination is
`<target-home>/<rel_path>` (Step 0 resolved `<target-home>`). For
`location: outside-home` items, use `abs_path` from the separate out-of-home
archive (Step 4b). NEVER use `source.home` as a destination.

### `skip`
Do nothing. Note the `reason` (e.g. `syncthing-managed`) in the report.

### `copy-if-absent`
Copy only if dest doesn't exist. Never overwrite.
```sh
dest="$target_home/<rel_path>"
[ -e "$dest" ] || sudo cp -a "<work>/<path>" "$dest"
```

### `append-dedup`  (secrets like authorized_keys, known_hosts)
Append only lines not already present. Preserve perms. Never log contents.
```sh
# example for authorized_keys-style files; operate line-wise, dedup, then chmod 600
```
For `.ssh`: merge `authorized_keys`/`known_hosts`/`config` by append-dedup;
copy private keys only if absent (`copy-if-absent` semantics);
`chmod 700 "$target_home/.ssh"`, `600` keys. For `.gnupg`: prefer `copy-if-absent`
of the whole dir if target has no keyring; otherwise guide the user through
`gpg --import` rather than copying over a live keyring.

### `rsync`  (opt-in large dirs; may be `transport: sidecar`)
```sh
# bundle items live under ~/migrations/work/<root>/; sidecar items under
# ~/migrations/incoming/<host>-<date>-sidecar/
sudo rsync -aHAX "<src>/" "$target_home/<rel_path>/"     # NEVER --delete
```

### `review-diff`  (shell rc, gitconfig, dotfiles)
Show the user a diff and integrate interactively. Never blind-overwrite.
```sh
diff -u "$target_home/<rel_path>" "<work>/<path>" || true
```
Recommend a merge; let the user choose. Note zsh↔bash differences when a macOS
source's `.zshrc` lands on a bash target (don't just append zsh syntax to bash).

### Inert-payload check (text files)
When integrating a text file, you MAY scan it for embedded absolute paths that
won't exist here (notably `source.home`, e.g. `/Users/mac-user`, and other machine
paths). Do NOT auto-rewrite. **Report** matches to the human with the file and
line, and let them decide (edit, leave, skip):
```sh
grep -nF "$(jq -r .source.home manifest.json)" "$dest" 2>/dev/null   # report only
```

### `union-dedup`  (bookmarks & tabs) → delegate to datatype target skills
Do NOT integrate browser items inline. Collect the staged `bookmarks.json` /
`tabs.json` paths from ALL bundles and hand them to the datatype target skills
(Step 5) so dedup and routing span every source.

**Ownership:** after writing anything into `<target-home>`, run
`sudo chown -R <target-user>:<target-group> "$target_home/<rel_path>"`.

---

## Step 4b — Out-of-home content (separate archive, absolute paths)

If the bundle declares `bundle.outside_home_archive`, it holds opt-in content
that lives OUTSIDE any home dir (absolute paths, chosen by the human on the
source). These items have `location: "outside-home"` and an `abs_path`.

- Present each out-of-home item to the human and confirm before writing (these
  touch system locations).
- Place at its `abs_path`; apply the item's `merge` strategy; fix ownership to
  whatever is appropriate for that path (often `root:root` — confirm).
- Same inert-payload rule: examine text contents, report issues, never auto-rewrite.

---

## Step 5 — Browsers (delegate to datatype target skills)

Browser data is integrated by dedicated **datatype target skills**, NOT by this
orchestrator directly. They consume the shared **url-groups** format, merge/dedup
across all bundles, and route each group to a destination (browser via injection
leaf, or a sink like Linkwarden / plain list) with the user.

| Datatype | Skill to load | Reads from each bundle |
|----------|---------------|------------------------|
| Bookmarks | `browser-bookmarks-target` | `browsers/<host>/<browser>/<profile>/bookmarks.json` |
| Open tabs | `browser-tabs-target`      | `browsers/<host>/<browser>/<profile>/tabs.json` |

For each datatype present in the bundles:
1. **Load** the corresponding target skill (via the `skill` tool).
2. Follow it: it collects every source's files, merges/dedups (never losing the
   target's existing data), presents the groups, and routes each — per the user's
   choices — to an injection leaf or a sink. Where a destination has no leaf yet,
   it emits a portable fallback file (Netscape HTML for bookmarks; a "Recovered
   tabs" URL list/HTML for tabs) for manual import.

Key guarantees these skills enforce (so you don't repeat them here):
- **Bookmarks:** additive union+dedup by URL; dated "Migrated from <host>" folders
  kept; existing target bookmarks never overwritten; folder hierarchy preserved.
- **Tabs:** URL preservation; each window/flat-pool group routed independently;
  nothing lost (fallback file if no leaf).
- **Browser absent on target:** the datatype skill surfaces it; the user routes
  those groups elsewhere (another browser, Linkwarden, or list) or installs the
  browser (requires approval).

> Cookies/localStorage and other datatypes will follow the same pattern
> (`browser-cookies-target`, …) as their skills are added. This pass covers
> bookmarks and tabs.

---

## Step 6 — Verify the result

- `sudo -u <target-user> ssh -T git@github.com` (or relevant host) — SSH keys work.
- `sudo -u <target-user> gpg --list-keys` — GPG keys present (if migrated).
- Browsers launch; bookmark count ≥ sum of (target + all sources) after dedup.
- Report (do not rewrite) any migrated text config still referencing the source
  host, `source.home`, `/Users/<name>`, or another machine's paths.
- `find "$target_home"/<migrated paths> ! -user <target-user>` — no stray
  `root:root` files.

---

## Step 7 — Report & decide bundle fate

Report to the user:
- **Migrated:** items integrated, per category.
- **Skipped:** with reasons (Syncthing-managed, etc.).
- **Manual:** macOS keychain secrets, browsers to install, anything needing the
  user's hands.
- **Inventory delta:** apps installed on each source but not here (report only —
  never auto-install).

Then ask the user what to do with the bundle(s) in `~/migrations/incoming/`:
1. **Delete** them (integration verified, no longer needed), or
2. **Keep as backup** → move to long-term storage.
```sh
mkdir -p ~/migrations/archive/
mv ~/migrations/incoming/<bundle> ~/migrations/archive/   # if user chooses keep
```
Do NOT delete or move without explicit user approval. The bundle is a
point-in-time backup until the user says otherwise.

---

## Multi-source ordering

When several bundles are present:
1. Integrate non-browser items bundle-by-bundle (Step 4).
2. Run the browser merge ONCE across all bundles (Step 5) so dedup is global.
3. Single consolidated report (Step 7).

If two sources conflict on the same `review-diff` file (e.g. both have a
`.gitconfig`), present both to the user and let them pick/merge.

---

## Safety checklist

- [ ] Destination account(s) resolved WITH the human (Step 0); not assumed
- [ ] `schema` understood; `bundle.format` decompressor present
- [ ] Checksums verified before integration
- [ ] No existing human data overwritten (additive / copy-if-absent / review-diff)
- [ ] Secrets: perms preserved, contents never logged
- [ ] In-home items placed at `<target-home>/<rel_path>`; source paths never used as dests
- [ ] Embedded absolute paths in text files REPORTED (not rewritten)
- [ ] All writes into `<target-home>` re-chowned to `<target-user>:<target-group>`
- [ ] Out-of-home items (if any) confirmed per-item before writing
- [ ] Bookmarks/tabs unioned + dated folders; nothing lost
- [ ] Browsers-not-present and macOS keychain surfaced as manual
- [ ] Inventory delta reported, nothing auto-installed
- [ ] User decided bundle fate (delete / archive)
- [ ] Maintenance report updated (no secret contents)

## Related skills

- `browser-bookmarks-target`, `browser-tabs-target` — datatype target skills this
  orchestrator delegates browser data to.
- `MANIFEST.md` — bundle contract. `../browser-bookmarks-source/FORMAT.md` —
  url-groups format.

Base directory for this skill: file:///home/domovoy/.agents/skills/user-migration-target
Relative paths (e.g., `MANIFEST.md`) are relative to this base directory.
