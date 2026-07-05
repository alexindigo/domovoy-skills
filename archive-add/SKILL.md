---
name: archive-add
description: Use when a user asks to add files to an existing archive (.tar.gz, .tar, .zip). Covers safe extract-append-repack workflow, verification, and cleanup.
---

# Archive Add / Modify

## Rules

- **Never modify a compressed archive in-place.** `tar rf` (append) only works on uncompressed `.tar`. For `.tar.gz`, `.tar.xz`, `.zip`: extract first.
- **Ask before removing originals** — even if the user's wording implies deletion, confirm explicitly.
- **Verify the new archive** before deleting originals.

## Workflow

### 1. Examine the existing archive

```bash
tar tzf <archive>       # list contents
```

### 2. Extract to a temp directory

```bash
mkdir -p /tmp/archive-work
cd /tmp/archive-work
tar xzf <original-archive>
```

### 3. Copy new files into the extracted tree

Maintain the same relative paths as the original archive structure.

### 4. Re-pack

```bash
tar czf <new-archive> *
```

### 5. Verify

```bash
tar tzf <new-archive>          # list all entries
# Check critical files are present
tar tzf <new-archive> | grep <file>
```

### 6. Replace original

```bash
cp <new-archive> <original-path>
```

### 7. Clean up temp directory

```bash
rm -rf /tmp/archive-work
```

### 8. Remove originals (only after explicit user confirmation)

```bash
rm <source-file-1> <source-file-2>
```
