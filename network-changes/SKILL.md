---
name: network-changes
description: Use when making changes to nftables, NetworkManager dispatchers, firewall rules, or any network configuration that could drop connectivity. Always create a change script + rollback script before applying.
---

# Network Changes

Changes to nftables, NetworkManager dispatchers, or other network config can
drop SSH, Wifi, or other active connections. Always follow the safe workflow.

## Safe workflow

1. **Create a change script** that applies the new configuration atomically.
   Verify syntax first with `nft -c -f <file>` or `bash -n <file>`.

2. **Create a rollback script** that undoes every change.
   The rollback must restore the exact previous state of every file touched.

3. **Place both scripts in `/tmp/`** so they're accessible even if the session
   loses its working directory.

4. **Present the scripts to the user** with a clear description of each step,
   and explain what to do if connectivity drops (run the rollback script).

5. **Let the user run the change script.** Do NOT run it from inside opencode.
   If the change drops SSH, opencode itself loses its connection.

6. **The rollback script is the user's escape hatch** — if things go wrong,
   they run the rollback script from a console (physical or recovery) and
   connectivity is restored.

### For nftables specifically

- NEVER apply a default-drop output chain without first staging it behind
  a script the user runs.
- The user must have a rollback script ready **before** the change is applied.
- If applying from an SSH session, the user should have a local console or
  BMC/IPMI open as backup.

### For NM dispatchers

- If a dispatcher script exits with an error, NM logs the failure but does
  NOT isolate the interface. The user will still have connectivity.
- To disable a faulty dispatcher: `chmod -x <file>` then
  `systemctl reload NetworkManager`.
- Rollback script should restore the original executable bit and content.

## Script conventions

- Place in `/tmp/<descriptive-name>-change.sh` and `/tmp/<name>-rollback.sh`.
- Both must be shell scripts with `set -euo pipefail` at the top.
- Both must print clear step-by-step output so the user knows what's happening.
- Rollback must be runnable multiple times (idempotent) — no errors if already
  rolled back.
