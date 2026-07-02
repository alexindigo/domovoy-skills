---
name: maintenance-report
description: Load at the start of EVERY session. Defines format, location, and logging rules for the daily maintenance binlog at ~/maintenance/reports/.
---

# Maintenance Report

Maintain a running log of every session in `~/maintenance/reports/`. This is the **first fallback** if the system is broken and opencode can't launch — a human must be able to trace what happened.

## File convention

One file per day: `~/maintenance/reports/YYYY-MM-DD.md`

Append to the existing file if one already exists for today; create it if not.

## Entry format

Each logged action gets a block:

```markdown
## HH:MM — Short headline

**Why:** Brief context — what problem or goal prompted this.

**What:** The actual command(s) run, or the action taken.

**Result:** What happened — success, failure (with error), or pending.

**Next:** (optional) What this unblocks or what to do next.
```

## When to log

Log every command that **changes state** — installs, writes, deletes, configures, reboots. Also log any non-trivial read that produced important diagnostics (journalctl, dmesg, lspci, etc.).

Safe reads (`ls`, `grep` for exploration, `pacman -Q`, etc.) do **not** need individual entries. Batch them into one "exploration" entry if they produced useful context.

## Report header

At the very top of each day's file, include a header:

```markdown
# Maintenance Report — YYYY-MM-DD

**Session start:** HH:MM
**User:** root
**Purpose:** <one-line summary of the session goal>
```

## Cleanup

Reports older than 90 days may be safely pruned. Keep at least the last 30 days at all times.
