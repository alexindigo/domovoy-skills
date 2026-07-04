---
name: syncthing-setup
description: Set up and reason about Syncthing for a Domovoy fleet — the leaf/hub architecture where leaf machines hold only the current copy and a central NAS/home server keeps file-versioning history as backup. Covers device-ID carryover during migration, shared folders (agents + setup), .stversions auto-ignore, and NAS-side versioning configuration. Use when configuring Syncthing on a new machine or the central server.
license: GPL-3.0-or-later
compatibility: opencode
metadata:
  family: infrastructure
  topic: syncthing
---

# syncthing-setup

How Domovoy uses Syncthing to sync its identity and machine profiles across a
fleet, and how to set it up on a new machine or the central home server.

> **Network-service caution:** Syncthing listens on the network. Per the core
> rules, NEVER enable the Syncthing GUI listen address or open ports without
> explicit user approval. The setup below keeps the GUI local/disabled and syncs
> over Syncthing's own encrypted transport + relays.

---

## Architecture: leaf machines + central hub

```
   leaf: laptop  ─┐
   leaf: <leaf>  ─┼── sync CURRENT copy ──►  NAS / home server (hub)
   leaf: ...     ─┘                           └─ File Versioning ON
                                                 (= back-history / backup)
```

- **Leaf machines** (each Domovoy's workstation): File Versioning **OFF**. They
  hold only the *current* copy of each folder. Lean, no `.stversions/` clutter.
- **Central hub** (NAS / always-on home server): File Versioning **ON**. It keeps
  the historical revisions — the fleet's time-machine / backup.

Rationale: versioning is **per-device**, so you enable it only on the hub. If a
leaf accidentally deletes or corrupts a file and it syncs out, the hub captures
the pre-change version in `.stversions/` *before* applying the change — so you can
always recover from the hub, even though leaves keep no history themselves.

---

## Shared folders

Domovoy syncs two folders (small, text — skills/configs/profiles):

| Folder ID | Path (leaf) | Contents |
|-----------|-------------|----------|
| `domovoy-agents` | `~/.agents` | skills + `AGENTS.md` (Domovoy identity) |
| `domovoy-setup`  | `~/setup`   | `setup/<hostname>/` machine profiles |

Both are `sendreceive`. Folder IDs are fleet-wide constants (`domovoy-*`) so every
machine and the hub agree.

---

## `.stversions` is auto-ignored — do NOT add ignore rules

`.stversions/` (like `.stfolder`) is a **reserved internal directory**. Syncthing
hard-codes special handling:

- never scanned as content, never synced to other devices, never needs `.stignore`.

So the hub's version history in `.stversions/` **never propagates** to the leaves —
automatically, zero config on either side. **Do not add `.stversions` to any
ignore list.**

Caveat: this auto-exemption applies to the **default** `.stversions` at the folder
root. If you set a custom `versioning.fsPath` *inside* the folder with a different
name, it would NOT be exempt and could sync. Keep versioning at the default
location (or point it outside the shared folder).

---

## Set up a NEW LEAF machine

1. Install syncthing; run as the domovoy **user service** (lingering enabled):
   ```sh
   systemctl --user enable --now syncthing.service   # as domovoy
   ```
2. Keep the GUI local only (default `127.0.0.1:8384`) — do NOT expose it.
3. Pair with the hub device (exchange device IDs).
4. Share/accept `domovoy-agents` → `~/.agents` and `domovoy-setup` → `~/setup`.
5. Leave File Versioning **OFF** (leaf default).
6. Verify both folders reach "Up to Date".

### Headless leaf pairing (no GUI)

If the GUI is disabled (BOOTSTRAP fleet standard), pairing must be done via
direct config.xml edits. The principle: pre‑declare the folders and device
IDs in config.xml, restart, and Syncthing auto-accepts — no click needed.

1. Add the hub's device ID to `/home/domovoy/.config/syncthing/config.xml`:
   ```xml
   <device id="<hub-device-id>" name="hub" compression="metadata" introducer="false" ...>
       <address>dynamic</address>
       <paused>false</paused>
       <autoAcceptFolders>false</autoAcceptFolders>
   </device>
   ```
2. Add device bindings inside each pre-declared folder — list both the local
   device and the hub:
   ```xml
   <folder id="domovoy-agents" ... ignorePerms="true" ...>
       ...
       <device id="<local-device-id>" introducedBy=""></device>
       <device id="<hub-device-id>" introducedBy=""></device>
   </folder>
   ```
   > `ignorePerms="true"` is critical: UID/GID differ across machines.
   > Without it, Syncthing fails on ownership mismatch for synced files.
3. Restart syncthing:
   ```sh
   systemctl --user restart syncthing.service
   ```
4. Check logs for connection and sync status:
   ```sh
   journalctl --user -u syncthing.service --no-pager -n 30
   ```
5. Verify both folders reach "Up to Date".

The hub must also have the leaf's device ID added on its side (or share the
folders to the leaf's device ID). Once both sides have each other's IDs,
syncing proceeds automatically through relays or direct LAN connection.

---

## Set up the CENTRAL HUB (NAS / home server)

1. Install syncthing on the always-on server.
2. Pair each leaf device.
3. Accept the shared folders `domovoy-agents` / `domovoy-setup` at a chosen path
   on the server.
4. **Enable File Versioning** on each folder (this is the whole point of the hub):
   - **Staggered** (recommended for text/config) — dense recent history thinning
     over time. Set *Maximum Age* (e.g. `365` days; `0` = keep forever).
   - or **Trash Can** — simple recycle bin; set *Clean out after* N days.
   For small text data, space cost is negligible.
5. `.stversions/` is created at each folder's root automatically and is never
   synced back to leaves — no action needed.

Example versioning config (XML, per folder on the hub):
```xml
<folder id="domovoy-agents" ...>
  <versioning type="staggered">
    <cleanupIntervalS>3600</cleanupIntervalS>
    <fsPath></fsPath>
    <fsType>basic</fsType>
    <param key="maxAge" val="31536000"></param>  <!-- 1 year in seconds -->
  </versioning>
</folder>
```

---

## Device-ID carryover (during user migration / rename)

When migrating Syncthing between users or homes on the SAME machine (e.g. an
`assistant` → `domovoy` rename), preserve the **device identity** so the hub sees
the *same* device, not a new one:

- The device ID is derived from `key.pem` + `cert.pem` in the Syncthing config dir.
- **Copy `key.pem` and `cert.pem`** (plus `config.xml`) to the new config dir; the
  new instance keeps the same device ID.
- Update `config.xml`: rewrite folder **paths** to the new home, and (optionally)
  folder **IDs**/labels.
- **Never run two instances with the same device ID simultaneously.** Stop the old
  instance before starting the new one; `disable` the old service so it can't
  auto-start on reboot and collide.

### Folder-ID rename tradeoff
If you also rename folder IDs (e.g. `assistant-*` → `domovoy-*`), the hub treats
them as **new folders** (must accept + drop the old ones) — content is identical so
block-hashing means no real re-transfer. If you keep the original IDs and change
only paths/labels, the hub sees the *same* folders (seamless, no re-accept). Choose
per your appetite for a clean name vs. a seamless hub transition.

---

## Verify

- Leaf: `.stfolder` marker present in each shared folder; folder shows "Up to Date".
- Hub: folders "Up to Date"; `.stversions/` appears after the first
  replace/delete.
- Sizes on hub roughly match the leaf's content (leaf `du` may differ slightly due
  to `.git`/`.stfolder`/block accounting — the hub's "synced" status is authoritative).

Base directory: file:///home/domovoy/.agents/skills/syncthing-setup
