---
name: numbered-backup
description: Create safe numbered backups of files before modifying them. Uses .bak, .1.bak, .2.bak, ... — never overwrites an existing backup. Referenced by network-changes and add-service skills. Covers creation, rollback, and cleanup conventions.
license: GPL-3.0-or-later
compatibility: opencode
metadata:
  family: infrastructure
  topic: safety
  related: [network-changes, add-service]
---

# numbered-backup

Safe backup convention for files before modification. The first backup gets
`.bak`; if that exists, `.1.bak`, `.2.bak`, and so on. Never overwrites
an existing backup — every edit leaves a full trail.

## Convention

| Run | Backup name | Notes |
|---|---|---|
| 1st edit | `file.bak` | Original state preserved |
| 2nd edit | `file.1.bak` | `file.bak` already exists |
| 3rd edit | `file.2.bak` | Next available number |
| ... | `file.N.bak` | Always find the next unused number |

Backups are colocated with the original file — easy to find, easy to roll back.

## Usage in scripts

```bash
backup "$CONF"
```

The `backup` function creates the numbered backup and sets `BAK` to the
chosen filename. Scripts use:

```bash
source /usr/local/bin/numbered-backup   # or inline the function

backup /etc/nftables.conf
echo "backed up to $BAK"
# ... modify the file ...
# rollback: cp "$BAK" /etc/nftables.conf
```

### Inline snippet (no external dependency)

If you can't depend on `/usr/local/bin/numbered-backup` being installed
everywhere, inline the two-liner:

```bash
BAK="${CONF}.bak"
if [ -e "$BAK" ]; then N=1; while [ -e "${CONF}.${N}.bak" ]; do ((N++)); done; BAK="${CONF}.${N}.bak"; fi
cp -a "$CONF" "$BAK"
```

## Rollback

Rollback scripts know the backup name (store it, or find the highest-numbered
variant). After restoring:

```bash
cp "$BAK" "$ORIGINAL"   # restore
rm "$BAK"               # clean up
```

## Cleanup

Backups are kept indefinitely. Old ones can be pruned manually:

```bash
rm /etc/nftables.conf.*.bak /etc/nftables.conf.bak
```

Default: leave them. They cost kilobytes and provide a full audit trail of
who modified what, in what order, and what the previous states were.

## Related

- **network-changes** — uses this convention for nftables/dispatcher change scripts
- **add-service** — uses this convention before `sed -i` on `/etc/nftables.conf`

Base directory: file:///home/domovoy/.agents/skills/numbered-backup
