---
name: domovoy-scripts
description: Conventions for writing scripts that interact with or modify domovoy's user-level systemd services from outside its own shell — bootstrapping, migration, admin one-shots (restart opencode to load a new model, reload after config edits), or any human session managing domovoy's services. Covers the mandatory inline sudo pattern for systemctl --user, file placement, ownership, and trigger-script conventions with rollback.
license: GPL-3.0-or-later
compatibility: opencode
metadata:
  family: infrastructure
  topic: scripting
  related: [configure-local-models, system-documentation, git-repo-identity]
---

# domovoy-scripts

Conventions for writing scripts that interact with domovoy's user-level
systemd services from **outside domovoy's own shell.** The same pattern
applies whether the caller is root (bootstrap/migration), a human user
(routine admin), or another account managing domovoy's services.

## Common contexts

- Bootstrapping a fresh domovoy user (from root)
- Root → domovoy migration cutover scripts
- Restarting opencode after a config edit
- Reloading opencode to pick up a newly downloaded local model
- Restarting syncthing after config.xml changes
- Rebuilding authorized_keys when a new ssh.pub arrives via Syncthing
- Any one-shot admin task that touches domovoy's user services

## 1. Who runs what, and where scripts live

Three tiers of scripts, each with a canonical location based on **who executes
them** and **how often.**

| Who runs it | Frequency | Location | Example |
|---|---|---|---|
| root (bootstrap, migration) | One-shot | `/tmp/` | `migrate.sh`, `bootstrap-domovoy.sh` |
| Human user or root, repeatedly | Persistent | `~/bin/` or `/usr/local/bin/` | `domovoy-restart`, `domovoy-reload-models` |
| systemd (as `domovoy`) | Automatic | `~domovoy/.local/bin/` | `opencode-health-check` |

The "human user" role varies by machine — check `setup/<hostname>/IDENTITY.md`
for the human account name and home path.

**Never** mix these tiers:
- Don't put a one-shot deploy script in a persistent location — it clutters.
- Don't put a systemd-invoked script in a human user's bin — the domovoy user
  can't read it (human home is `drwx------`).
- Don't put persistent user scripts in `/tmp/` — they disappear on reboot.

## 2. The systemctl sudo pattern (MANDATORY)

When calling `systemctl --user` for a different account via `sudo`, the
environment variable `XDG_RUNTIME_DIR` is required to locate the target
user's systemd bus at `/run/user/<uid>/bus`.

**Incorrect — will fail with "Failed to connect to user scope bus":**

```bash
export XDG_RUNTIME_DIR=/run/user/588
sudo -u domovoy systemctl --user restart opencode.service
```

**Why it fails:** `sudo` drops most environment variables by default.
`XDG_RUNTIME_DIR` set via `export` is stripped. systemctl can't find the
domovoy user's D-Bus session.

**Correct — inline variable assignment:**

```bash
sudo -u domovoy XDG_RUNTIME_DIR=/run/user/588 systemctl --user restart opencode.service
```

The inline `VAR=value` syntax is passed through `sudo` to the child process.
This is the **only** way to pass environment variables through sudo.

This pattern applies to every cross-user `systemctl --user` invocation:
root→domovoy during bootstrap, human→domovoy during admin operations —
anything that isn't domovoy's own login shell.

## 3. File ownership and permissions

| Location | Owner | Permissions | Notes |
|---|---|---|---|
| `/tmp/<script>` | doesn't matter | `755` | One-shot, disposable — bootstrap, migration, admin |
| `~<human>/bin/<script>` | `<human>:<human>` | `755` | Persistent human-user scripts |
| `/usr/local/bin/<script>` | `root:root` | `755` | System-wide admin utilities |
| `~domovoy/.config/systemd/user/<unit>` | `domovoy:domovoy` | `644` | Service unit files |
| `~domovoy/.local/bin/<script>` | `domovoy:domovoy` | `755` | systemd-invoked tools |

**Never** leave `root:root` owned files in a human user's home directory. If
you use `sudo` to create a file in a user's home, fix ownership afterwards.

## 4. Trigger / deploy script pattern

For multi-step setup tasks (new service, config changes), create a single
**trigger script** in `/tmp/`. The operator runs it once, then removes it
(or it self-destructs on reboot).

### Baseline requirements

Every trigger script MUST:

- Use `set -euo pipefail` — stop on error, unset variable, OR pipeline failure.
  `set -eu` alone lets piped failures slip through silently.
- Install an `ERR` trap that reports the line number so the operator can see
  exactly where the script broke.
- Roll back partial state changes if a later step fails. If step 1 renames
  a file and step 2 fails, step 1 must be undone.
- Number the steps as `==> N/M:` so the operator sees progress.
- Never guess about opencode restart — either restart explicitly (as the
  last step) or print instructions and stop. The assistant itself never
  restarts opencode; the operator-run script may.

### Common gotcha — `systemctl enable` on `Wants=`-only units

Oneshot service units pulled in via `Wants=` from another unit do NOT belong
in an `[Install]` section. Running `systemctl --user enable <oneshot>.service`
on such a unit prints a warning and exits non-zero. Just run `daemon-reload` —
the parent unit's `Wants=` handles activation. Don't `enable` unless the unit
has its own `[Install]` section.

### Template with error handling + rollback

```bash
#!/bin/bash
set -euo pipefail

TMP_DIR="/tmp"
DOMOVOY_ENV="XDG_RUNTIME_DIR=/run/user/588"

# Track what we've done so rollback knows what to undo
STATE_RENAMED=0

rollback() {
    local exit_code=$?
    local line=$1
    echo "FAILED at line $line (exit $exit_code)" >&2
    if [ "$STATE_RENAMED" = "1" ]; then
        echo "  rollback: undoing rename..." >&2
        mv "$TMP_DIR/newname" "$TMP_DIR/oldname" 2>/dev/null || true
    fi
    exit "$exit_code"
}
trap 'rollback $LINENO' ERR

echo "==> 1/N: Rename <oldname> to <newname>"
mv "$TMP_DIR/oldname" "$TMP_DIR/newname"
STATE_RENAMED=1
echo "    done."

echo "==> 2/N: Reload systemd"
sudo -u domovoy $DOMOVOY_ENV systemctl --user daemon-reload
echo "    done."

echo "==> N/N: Restart opencode"
sudo -u domovoy $DOMOVOY_ENV systemctl --user restart opencode.service
sleep 2
sudo -u domovoy $DOMOVOY_ENV systemctl --user status opencode.service \
    --no-pager -l 2>&1 | head -20

echo ""
echo "Done."
```

### Atomic file writes (for config-mutating scripts)

When a script rewrites a config file, write to `<file>.tmp` then rename —
a crash mid-write leaves the original untouched.

```python
# Python example
with open(CONFIG + ".tmp", "w") as f:
    json.dump(config, f, indent=2)
    f.write("\n")
os.rename(CONFIG + ".tmp", CONFIG)  # atomic on POSIX
```

Never write directly to the destination. A corrupted `opencode.jsonc` can
break the whole server.

## 5. Hardcoded values to verify

- **Domovoy UID:** `588` — used for `XDG_RUNTIME_DIR=/run/user/588`.
  Verify with `id -u domovoy`.
- **Domovoy systemd user dir:** `~domovoy/.config/systemd/user/` —
  all user-scoped service units go here.
- **Human user account:** check `setup/<hostname>/IDENTITY.md` for the
  human account name and home path — varies per machine.

## 6. Common recipes

### Restart opencode (config edit, new model)

```bash
#!/bin/bash
set -euo pipefail
# Restart opencode to pick up config changes or a new local model
sudo -u domovoy XDG_RUNTIME_DIR=/run/user/588 systemctl --user restart opencode.service
sleep 2
sudo -u domovoy XDG_RUNTIME_DIR=/run/user/588 systemctl --user status opencode.service --no-pager -l 2>&1 | head -20
echo "Reconnect your client — the server was restarted."
```

### Reload opencode (graceful, keeps connections)

```bash
#!/bin/bash
set -euo pipefail
sudo -u domovoy XDG_RUNTIME_DIR=/run/user/588 systemctl --user reload opencode.service 2>/dev/null \
    || sudo -u domovoy XDG_RUNTIME_DIR=/run/user/588 systemctl --user restart opencode.service
```

### Restart syncthing after config.xml edit

```bash
#!/bin/bash
set -euo pipefail
sudo -u domovoy XDG_RUNTIME_DIR=/run/user/588 systemctl --user restart syncthing.service
sleep 2
sudo -u domovoy XDG_RUNTIME_DIR=/run/user/588 journalctl --user -u syncthing.service --no-pager -n 15
```

### Rebuild authorized_keys after new ssh.pub arrives

```bash
#!/bin/bash
set -euo pipefail
sudo -u domovoy XDG_RUNTIME_DIR=/run/user/588 systemctl --user start domovoy-ssh-gateway.service
sudo -u domovoy XDG_RUNTIME_DIR=/run/user/588 systemctl --user status domovoy-ssh-gateway.path
```

### Migration one-shot template

```bash
#!/bin/bash
set -euo pipefail
# Root → domovoy bootstrapping tasks
DOMOVOY_HOME="/home/domovoy"
DU_CMD="sudo -u domovoy XDG_RUNTIME_DIR=/run/user/588"

echo "==> 1/4: Copy service templates"
cp /path/to/templates/opencode.service    "$DOMOVOY_HOME/.config/systemd/user/"
cp /path/to/templates/opencode-health.*   "$DOMOVOY_HOME/.config/systemd/user/"
chown -R domovoy:domovoy "$DOMOVOY_HOME/.config/systemd/user"

echo "==> 2/4: Reload systemd"
$DU_CMD systemctl --user daemon-reload

echo "==> 3/4: Enable services"
$DU_CMD systemctl --user enable --now opencode.service opencode-health.timer opencode-restart.timer

echo "==> 4/4: Verify"
$DU_CMD systemctl --user status opencode.service --no-pager -l | head -10
echo "Done. Reconnect to port 4096."
```

## 7. Checklist before writing a script

1. **Who runs it?** → determines location and ownership
2. **How often?** → persistent (`~/bin`, `/usr/local/bin`) vs one-off (`/tmp`)
3. **Does it touch systemctl?** → use inline `XDG_RUNTIME_DIR=` pattern
4. **Does it restart opencode?** → the assistant itself never restarts; an
   operator-invoked script may. Decide: restart as the last step, or just
   print instructions.
5. **Ownership correct?** → check `setup/<hostname>/IDENTITY.md` for the
   human account; domovoy:domovoy for system paths
