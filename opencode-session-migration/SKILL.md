---
name: opencode-session-migration
description: Rewrite session database rows after migrating opencode from one user home to another (root → domovoy, prior agent → domovoy, etc.). Copying opencode.db is not enough — the session `directory`, session `path`, and message `data.cwd` columns must be rewritten or the TUI client filters sessions out. SQLite WAL mode allows live updates. Use after the file-copy step of MIGRATION.md.
license: GPL-3.0-or-later
compatibility: opencode
metadata:
  family: infrastructure
  topic: migration
  related: [domovoy-scripts]
---

# opencode-session-migration

After copying opencode data from one user's home to another (e.g. during a
root → domovoy or prior-agent → domovoy migration), the session database at
`~/.local/share/opencode/opencode.db` contains rows with the OLD home path.
**Copying the file is not enough** — the TUI client filters sessions by the
`path` column and will not show migrated sessions until the rows are rewritten.

This skill covers the DB rewrite step. Run it AFTER the file-copy step in
MIGRATION.md, and BEFORE restarting opencode.

## 1. What breaks if you skip this step

The TUI client filters sessions by both `session.directory` (absolute path)
and `session.path` (same path, minus the leading `/`). After a file copy,
old sessions still reference the source home (e.g. `/root` or `/home/assistant`)
and are invisible in the session list. The data *exists* in opencode.db — the
client just cannot find it.

## 2. The three columns that need rewriting

| Column | Table | Old value (source home) | New value (target home) | Example old → new |
|--------|-------|------------------------|------------------------|---------------------|
| `directory` | `session` | `OLD_HOME` (absolute) | `NEW_HOME` | `/root` → `/home/domovoy` |
| `path` | `session` | `NEW_HOME` minus leading `/` | same, but from NEW_HOME | `root` → `home/domovoy` |
| `data` (cwd field) | `message` | JSON blob contains `"cwd":"OLD_HOME/..."` | replace with NEW_HOME in the blob | `"cwd":"/root/..."` → `"cwd":"/home/domovoy/..."` |

## 3. The SQL

Replace the placeholders with concrete paths for this migration, then run:

```sql
-- Set these first (absolute paths, same pattern):
-- OLD_HOME = /root
-- NEW_HOME = /home/domovoy
-- NEW_PATH = home/domovoy      (NEW_HOME minus leading /)

-- Rewrite session directory
UPDATE session
   SET directory = 'NEW_HOME'
 WHERE directory = 'OLD_HOME';

-- Rewrite session path (home minus leading /)
UPDATE session
   SET path = 'NEW_PATH'
 WHERE path = 'OLD_PATH';

-- Rewrite cwd references in message data (JSON blobs)
UPDATE message
   SET data = REPLACE(data, '"cwd":"OLD_HOME', '"cwd":"NEW_HOME')
 WHERE data LIKE '%"cwd":"OLD_HOME%';
```

SQLite WAL mode allows these updates while opencode is running — the DB
handles concurrent reads. Still, a restart is needed afterward so the
in-memory session list picks up the new paths.

## 4. The history principle

**Only rewrite the functional artifact (the working opencode.db).** Leave
historical artifacts intact:

- **Loose files** in `log/`, `storage/`, `tool-output/` may contain literal
  old-home paths in their contents. These are historical records — the cwd
  *was* the old home at the time — and rewriting them would falsify history.
  They do not affect session visibility.

- **The source-home opencode.db** is also left unchanged. It is deleted
  later as part of source cleanup (see MIGRATION.md), not rewritten in place.

- **The maintenance report** should capture the SQL statements run so that a
  full binlog replay reaches the same final state.

## 5. Restart opencode to apply

The DB rows are updated, but opencode holds a cached session list in memory.
Restart the service:

1. Follow the `domovoy-scripts` skill for the restart script convention.
   The mandatory pattern is:

   ```bash
   sudo -u domovoy XDG_RUNTIME_DIR=/run/user/<uid> systemctl --user restart opencode.service
   ```

2. **NEVER restart opencode from inside opencode.** Create a script in
   `/usr/local/bin/` or `/tmp/` and ask the operator to run it from a
   console. If you are the operator running this skill interactively,
   run the command directly from a TTY.

## 6. Verification

After the updates (before restart):

```sql
-- Should return exactly one row: NEW_HOME
SELECT DISTINCT directory FROM session;

-- Should return exactly one row: NEW_PATH (home/domovoy)
SELECT DISTINCT path FROM session;

-- Should return 0
SELECT COUNT(*) FROM message
 WHERE data LIKE '%"cwd":"OLD_HOME%';
```

## 7. Edge cases

### Chained migrations

If opencode moved multiple times (e.g. `/root` → `/home/assistant` →
`/home/domovoy`), run the three SQL statements **twice**: once with
OLD_HOME=/root → NEW_HOME=/home/assistant, then again with
OLD_HOME=/home/assistant → NEW_HOME=/home/domovoy.

### Greeting session exclusion

Some older migrations exclude the very first Greeting session (which is
already in the new home after a fresh install). This is only needed if
open code pre-populated a session before the migration. Unless you know
a specific session was created in the new home before you moved data,
skip this — the simple column-based UPDATE covers all real sessions.

## 8. Related

- **domovoy-scripts** — the restart script conventions used in step 5
- **MIGRATION.md** — the full user-migration workflow that surrounds this step

Base directory: file:///home/domovoy/.agents/skills/opencode-session-migration
