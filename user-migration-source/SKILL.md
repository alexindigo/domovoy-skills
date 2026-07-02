---
name: user-migration-source
description: Orchestrate the SOURCE side of a one-way user-data migration between machines. Audits the user's data and settings with their guidance, drives per-datatype source skills (bookmarks, tabs, and more) to collect data into a portable migration bundle, and delivers it to the target. Use on the machine you are migrating away FROM.
license: GPL-3.0-or-later
compatibility: opencode
metadata:
  family: user-migration
  tier: orchestrator
  direction: source
---

# Skill: user-migration-source

You are running as the **SOURCE** in a user-data migration. Your job: **collect**
the human user's data and settings (with the user's guidance), **pack** them into
a self-describing *migration bundle*, and **deliver** that bundle to the target
machine's drop directory.

This skill pairs with `user-migration-target`. They communicate through a single
artifact — a `.tar.gz` (or `.tar.zst`) **migration bundle** containing a
versioned `manifest.json`. The transport (rsync-over-ssh, USB stick, or an unmounted
partition across a dual-boot reboot) is irrelevant: source packs a file, target
unpacks it. The bundle also serves as a point-in-time **backup**.

Read the shared contract before doing anything:
`../user-migration-target/MANIFEST.md`.

---

## Mental model — like an open-source Migration Assistant

```
SOURCE (this skill)                         TARGET (user-migration-target)
─────────────────                           ──────────────────────────────
 1. audit (WITH the user)
 2. stage selected items  ── manifest.json ──►  consumes contract
 3. pack tar.gz bundle
 4. deliver to target drop dir  ───────────►   ~/migrations/incoming/ (domovoy)
```

You DECIDE NOTHING IRREVERSIBLE. You only read source data and write a bundle.
All destructive integration happens on the target, with the user present.

---

## Golden rules

1. **Read-only on the user's live data.** Never move, delete, or modify the
   source user's files. Copy into staging only.
2. **The user guides classification.** Auto-detect what you can, but surface
   anything uncertain and let the user include/exclude it. Be *open-minded*:
   unknown-but-likely-important items get carried with a safe merge strategy,
   never silently dropped.
3. **Browsers must be CLOSED** before extracting bookmarks/tabs, or sessions
   won't be flushed to disk. Verify and ask the user to quit if needed.
4. **Skip Syncthing-managed folders.** If a folder already syncs to the target,
   record it as `skip` (reason `syncthing-managed`) — don't duplicate it.
5. **Never log secret contents.** SSH/GPG keys go into the bundle with perms
   preserved, but their bytes never appear in output, logs, or reports.
6. **Bundle lands where the `domovoy` user can write** on the target — under the
   target's domovoy home (domovoy-to-domovoy SSH), NOT a human account's home.
7. **Home is the root.** Store in-home items **relative to the account's home**
   (`rel_path`, e.g. `.ssh/config`). The bundle carries NO absolute source paths
   for in-home content — the target reconstructs under its own home. This makes
   the source account name/home irrelevant to placement.
8. **Out-of-home is opt-in & separate.** Only include content outside `$HOME` if
   the user asks; it travels in a SEPARATE archive with absolute paths.

---

## Step 1 — Detect platform & scope the human account(s)

```sh
uname -s        # Linux | Darwin
hostname
```
Branch ALL path logic on `Linux` vs `Darwin`. macOS uses `/Users/<name>`,
zsh by default, and `~/Library/...` for app data.

**Scope accounts WITH the user.** A machine may have several human accounts; you
do not assume the current one. List candidates and let the user choose which are
in scope (one bundle / `source` section per included account):
```sh
# Linux human accounts
getent passwd | awk -F: '$3>=1000 && $7!~/nologin|false/ {print $1"  uid="$3"  home="$6}'
# macOS human accounts
dscl . -list /Users UniqueID | awk '$2>=500 && $1!~/^_/ {print $1}'
```
For each included account record its identity for the manifest `source` section:
`account`, `uid`, `home`, `shell`, `os`. Everything below is **relative to that
account's `home`** (`rel_path`) — never store absolute in-home paths.

---

## Step 2 — Build the app inventory (informational)

The inventory tells the target what was installed on the source so the user can
decide what to reinstall. **You never install anything.**

### Linux (Arch)
```sh
pacman -Qqen     # explicitly installed, native repos
pacman -Qqem     # foreign / AUR
command -v flatpak >/dev/null && flatpak list --app --columns=application
```

### macOS
```sh
command -v brew >/dev/null && brew leaves            # top-level formulae
command -v brew >/dev/null && brew list --cask
command -v mas  >/dev/null && mas list               # App Store apps
ls /Applications /Applications/Utilities 2>/dev/null  # GUI apps
system_profiler SPApplicationsDataType 2>/dev/null    # full detail (slow)
```

Write each list into `inventory/` in the staging tree.

---

## Step 3 — Audit data categories (WITH the user)

Walk these categories. For each: detect presence, estimate size (`du -sh`),
present to the user, and confirm include/exclude. Record the decision in the
manifest with a merge strategy (see MANIFEST.md vocabulary).

| Category    | Linux source                         | macOS source                                   | Default merge      |
|-------------|--------------------------------------|------------------------------------------------|--------------------|
| `ssh`       | `~/.ssh`                             | `~/.ssh`                                        | `append-dedup` (secret) |
| `gpg`       | `~/.gnupg`                          | `~/.gnupg`                                       | `copy-if-absent` (secret) |
| `shell`     | `.bashrc .bash_profile .profile`    | `.zshrc .zprofile .zshenv`                       | `review-diff`      |
| `gitconfig` | `~/.gitconfig ~/.config/git`        | same                                            | `review-diff`      |
| `dotconfig` | selected `~/.config/*`              | selected `~/.config/*`                          | `copy-if-absent`   |
| `appdata`   | (n/a)                               | selected `~/Library/Application Support/*`       | `copy-if-absent`   |
| `bookmarks` | via `browser-bookmarks-source` (Step 4) | same                                       | `union-dedup`      |
| `tabs`      | via `browser-tabs-source` (Step 4)      | same                                       | `union-dedup`      |
| `dir`       | `~/Projects ~/aur ~/bin` etc.       | `~/Projects` etc.                               | `rsync` (opt-in)   |
| `userdirs`  | `~/Documents ~/Pictures` ...        | same                                            | check Syncthing    |

Paths above are shown `~/`-relative; each is stored as a home-relative `rel_path`
(e.g. `~/.ssh` → `rel_path: .ssh`). Never record absolute in-home paths.

**Open-minded discovery:** also scan top-level dotfiles and `~/.config/*` for
items not in the table. Present unknowns to the user; if included, record as
category `unknown` with `merge: copy-if-absent` and a `note`.

### Syncthing awareness
Before including any folder, check whether it's already a shared Syncthing folder
on BOTH source and target. If so, mark it `skip` / `syncthing-managed`.
```sh
# Linux
cat ~/.local/state/syncthing/config.xml 2>/dev/null
cat ~/.config/syncthing/config.xml 2>/dev/null
# macOS
cat "$HOME/Library/Application Support/Syncthing/config.xml" 2>/dev/null
```
Grep for `<folder ... path=`. Folders shared on both ends converge on their own.

### Big directories
For very large opt-in dirs, set `merge: rsync` and `transport: sidecar` — the
target pulls them *beside* the bundle rather than tarring hundreds of GB inside
it. Small/medium items go *inside* the bundle.

---

## Step 4 — Browsers (delegate to datatype source skills)

Browser data is handled by dedicated **datatype source skills**, NOT by this
orchestrator directly. Each owns a shared format and dispatches to per-browser
extraction leaves:

| Datatype | Skill to load | Output |
|----------|---------------|--------|
| Bookmarks | `browser-bookmarks-source` | `browsers/<host>/<browser>/<profile>/bookmarks.json` |
| Open tabs | `browser-tabs-source` | `browsers/<host>/<browser>/<profile>/tabs.json` |

For each datatype the user wants to migrate:
1. **Load** the corresponding source skill (via the `skill` tool).
2. Follow it: it detects browsers/profiles, ensures browsers are CLOSED (tabs),
   dispatches to per-browser extraction leaves, and writes validated JSON into the
   staging tree under `browsers/`.
3. Add its produced files + manifest entries to the bundle (the skill describes
   the exact manifest items: `category` `bookmarks`/`tabs`, `merge: union-dedup`).

These skills emit the shared **url-groups** format (see
`browser-bookmarks-source/FORMAT.md`): bookmarks grouped by folder, tabs grouped
by window (or flat-pool for Chromium/Brave). URLs/titles/structure only — never
secrets.

**Open tabs = URL preservation.** We preserve tab URLs (+ window grouping/order),
not native session state — the only model that survives cross-browser, cross-
platform routing on the target. No open tab's URL is lost.

If a browser has no extraction leaf yet, the datatype skill records it as
`unsupported` in the manifest and continues — migration is never blocked. A
browser present here but absent on the target is fine; the target routes its
groups to whatever destination the user picks.

> Cookies, localStorage, and other browser datatypes will follow the same
> pattern (`browser-cookies-source`, …) as their skills are added. This pass
> covers bookmarks and tabs.

---

## Step 4c — Out-of-home content (opt-in, ask + scan + select)

Ask the user whether anything OUTSIDE the account's home should be migrated. If
yes, offer to scan for non-system files/dirs outside `$HOME` and let the user
pick which to include:
```sh
# example: recently-modified, non-system paths outside home (present, don't auto-include)
find / -xdev -not -path "$HOME/*" \
  -not -path '/proc/*' -not -path '/sys/*' -not -path '/dev/*' \
  -not -path '/usr/*' -not -path '/var/lib/*' -newermt '-180 days' 2>/dev/null | head
```
Selected out-of-home items:
- Are recorded with `location: "outside-home"` and an absolute `abs_path`.
- Travel in a **SEPARATE archive** (`outside-home.tar`, referenced by
  `bundle.outside_home_archive`) because one tar can't cleanly mix relative and
  absolute entries.

---

## Step 5 — Stage everything

In-home items are staged **relative to the account's home** (no absolute paths):
```
~/.cache/user-migration-export/<host>-<iso8601>/
├── manifest.json
├── MIGRATION_README.md
├── inventory/
├── payload/       # in-home items at their rel_path (.ssh, .gnupg, .config/…)
├── browsers/      # datatype skill outputs (bookmarks.json / tabs.json)
├── outside-home.tar   # (optional) opt-in out-of-home items, ABSOLUTE paths
└── checksums.sha256
```
`payload/` mirrors the account's home layout by `rel_path` (e.g. `payload/.ssh`,
`payload/.config/foo`). Secrets keep strict perms; their bytes are never logged.

Copy with perms/xattrs preserved (into `payload/<rel_path>`):
```sh
# Linux
cp -a "$HOME/<rel_path>" "<staging>/payload/<rel_path>"
# macOS (bsd cp also supports -a)
cp -a "$HOME/<rel_path>" "<staging>/payload/<rel_path>"
```

Generate `manifest.json` per MANIFEST.md. Generate `MIGRATION_README.md` (human
summary: what's inside, what the target will do, manual items like macOS
keychain). Then checksums:
```sh
( cd <staging> && find . -type f ! -name checksums.sha256 -exec sha256sum {} + > checksums.sha256 )
# macOS: use `shasum -a 256` instead of `sha256sum`
```

---

## Step 6 — Pack the bundle

### Choose a format both ends can read

Compression compatibility is NOT uniform across platforms:

| Format | Arch          | Debian 12              | macOS                                   |
|--------|---------------|------------------------|-----------------------------------------|
| `gzip` | always (core) | always (`tar` builtin) | **always** (preinstalled)               |
| `zstd` | always (core) | `apt install zstd`     | NOT preinstalled (Homebrew / maybe libarchive) |

**Default to `gzip`.** `tar -czf` works out of the box on macOS, Debian 12, and
Arch with zero installs and is universally readable. The bundle is a one-time
transfer, and large directories go via the rsync *sidecar* (not inside the tar),
so compression ratio barely matters.

**Use `zstd` ONLY if BOTH source and target have it** (better ratio/speed). Pick
the format like this:
```sh
fmt=gzip
if command -v zstd >/dev/null 2>&1 && ssh domovoy@<target> 'command -v zstd >/dev/null 2>&1'; then
  fmt=zstd
fi
```

### Pack

```sh
cd ~/.cache/user-migration-export/

# gzip (default, universal):
tar -czf migration-bundle-<host>-<date>.tar.gz <host>-<date>/

# zstd (only if both ends confirmed to have zstd):
tar --zstd -cf migration-bundle-<host>-<date>.tar.zst <host>-<date>/
# bsdtar/macOS without --zstd support: pipe instead —
#   tar -cf - <host>-<date>/ | zstd -o migration-bundle-<host>-<date>.tar.zst
```

> xattrs/ACLs: GNU tar uses `--xattrs --acls`; bsdtar (macOS) uses different
> flags and they're rarely needed for user dotfiles. Only add xattr preservation
> if a specific item requires it; otherwise skip for portability.

**Record `bundle.format` (`gzip`|`zstd`) and `bundle.archive` (the filename) in
`manifest.json`** so the target verifies it has the right decompressor BEFORE
unpacking and uses the matching command.

---

## Step 7 — Deliver to the target drop dir

The drop dir lives under the **target's `domovoy` home** (writable over
domovoy-to-domovoy SSH):
```
<target>:~/migrations/incoming/
```

### Transport A — rsync over SSH (preferred for large files)
```sh
rsync -aHAX --info=progress2 \
  migration-bundle-<host>-<date>.tar.gz \
  domovoy@<target>:~/migrations/incoming/
# sidecar big dirs (merge: rsync) go beside it:
rsync -aHAX --info=progress2 <dir>/ domovoy@<target>:~/migrations/incoming/<host>-<date>-sidecar/<dir>/
```

### Transport B — USB / removable media
Copy the bundle to the media; tell the user the exact filename and where the
target should look (`~/migrations/incoming/` once mounted/copied).

### Transport C — dual-boot / encrypted disk handoff
Drop the bundle onto a location the target OS can read after reboot (e.g. the
target partition, or shared storage). Then:
> unlock source → pack → drop bundle → unmount → reboot into target →
> tell the target domovoy: *"continue migration as target host"*.

The bundle is the handoff token across the reboot boundary.

---

## Step 8 — Hand off

Tell the user the bundle is delivered and what to do next:
> On the target machine, tell the domovoy: **"continue the user migration as
> the target host"**. It will find the bundle(s) in `~/migrations/incoming/`,
> verify, unpack, and integrate — working with you on any conflicts.

If the source is an Arch machine with its own domovoy, you MAY be invoked
remotely by the target with a short prompt; run this skill autonomously through
Step 7, but still require the user to confirm browser-closed and big-dir opt-ins.

---

## Special cases

- **Same-host migration (e.g. USB-stick install → SSD):** run this skill while
  booted from the source, write the bundle to the destination filesystem's
  `~/migrations/incoming/` (mount it), reboot into the SSD install, then run
  `user-migration-target`. No network needed.
- **macOS keychain secrets** (Wi-Fi passwords, app tokens) CANNOT be rsynced or
  read portably. Document them in `MIGRATION_README.md` under "manual" so the
  user re-enters them on the target.

---

## Safety checklist before delivery

- [ ] Browsers were closed during extraction
- [ ] Secrets included with perms preserved; contents never logged
- [ ] Syncthing-managed folders marked `skip` with reason
- [ ] Unknown-but-included items recorded with a safe merge strategy
- [ ] `manifest.json` validates against MANIFEST.md schema
- [ ] `checksums.sha256` generated
- [ ] Archive name + format recorded in manifest
- [ ] User confirmed opt-in big directories
- [ ] Maintenance report updated (no secret contents)

## Related skills

- `browser-bookmarks-source`, `browser-tabs-source` — datatype source skills this
  orchestrator delegates browser data to.
- `../user-migration-target/MANIFEST.md` — bundle contract.

Base directory for this skill: file:///home/domovoy/.agents/skills/user-migration-source
