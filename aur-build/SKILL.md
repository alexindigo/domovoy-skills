---
name: aur-build
description: Use ONLY when installing or updating AUR packages. Covers the full manual workflow: check for updates (without fetching), clone/pull, PKGBUILD inspection, makepkg, pacman -U, and cleanup. Never use AUR helper tools.
---

# AUR Package Install / Update

## Check for updates (without fetching)
```bash
cd ~/aur/<pkgname>
# Show local commit and version
git log --oneline -3
head -10 PKGBUILD | grep -E 'pkgver|pkgrel'

# Check upstream HEAD without fetching
git ls-remote origin HEAD
```

Compare hashes — if they differ, an update is available.

## Clone or pull
```bash
# New package:
mkdir -p ~/aur && cd ~/aur
git clone <repo-url> <pkgname>

# Existing package (fetch + merge):
cd ~/aur/<pkgname> && git pull
```

## Examine PKGBUILD
Read the full PKGBUILD and show it to the user. First enumerate all functions:
```bash
grep -n '^[a-zA-Z_][a-zA-Z0-9_]*()' PKGBUILD
```

Then offer to show each function's body. When the user says "show &lt;name&gt; function", display the function body **with line numbers** in a code block so the user can see the exact content and spot potential dangers (obfuscation, suspicious URLs, dangerous commands). Read the file with `read` tool using the function's line range, then present it as:

```markdown
### `function_name()` (lines X-Y)
\`\`\`
1: line content
2: line content
...
\`\`\`
```

Check for:
- Unexpected `source` URLs (malware, cryptominers)
- Dangerous commands in `build()`, `package()` (rm -rf /, curl | bash, etc.)
- Pre-built binaries with no verifiable source
- Odd `curl`, `wget`, or network calls
- `chmod 777`, ownership changes without reason

## After PKGBUILD review — MANDATORY GATE

Once you have reviewed the PKGBUILD, you MUST do the following BEFORE running ANY command (makepkg, pacman, pip, or any dependency installation):

1. **Report findings**: "Found X dependencies: [list]. Issues found: [list if any, or 'none']."
2. **Ask**: "Proceed with build, or edit PKGBUILD first?"
3. **Wait** for explicit YES before running any command.

**If dependencies are missing, conflicting, or unnecessary:**
- **DO NOT** install them manually (no `pacman -S`, no `pip install`, nothing)
- **DO NOT** use `--assume-installed`, `--nodeps`, or any workaround
- **PROPOSE** specific PKGBUILD edits and **WAIT** for approval to make them
- Only after the user approves the edits OR chooses to proceed anyway, then you may continue

**If the review found no issues:**
- Still ask before proceeding. A clean review is not automatic permission.
- "PKGBUILD looks clean — no suspicious URLs, no dangerous commands. Proceed with build?"

## Pre-build checklist

After the user approves the PKGBUILD (including any edits to build(), package(),
or depends), you MUST create a command checklist BEFORE running anything.

1. **Estimate all commands** you expect to run to reach `makepkg -src`:
   - Any dependency installation needed before build
   - The build command itself
   - That's it — `makepkg -src` is the endpoint. Installation (`pacman -U`) is
     a separate step requiring separate approval. It is handled by the `aur-install` skill.

2. **Present the checklist** to the user:
   ```
   Build plan:
   1. makepkg -src
   That's it. No dependencies to install.
   ```

3. **Wait for approval** of the checklist.

4. **Execute ONLY what's on the list.** If a step fails and you need a new
   command (missing dependency, etc.), STOP. Present an updated checklist
   explaining why. Never add commands silently.

### Example failure flow

```
makepkg -src fails: "error: intel-oneapi-mkl-sycl not found"

✋ STOP. Do NOT install anything. Report:
"Build failed — missing MKL. Need to add package first.

Updated checklist:
 1. sudo pacman -S intel-oneapi-mkl-sycl  ← NEW
 2. makepkg -src

Proceed with updated list?"
```

## After build — STOP

`makepkg -src` succeeded. Mission accomplished. STOP.

Report to user:
```
Build done: llama.cpp-sycl-f16-server-b9828-1-x86_64.pkg.tar.zst
```

That's it. Do not suggest `pacman -U`. Do not ask about installation.
Do not mention installing. The user decides when, where, and how to
install — that is handled by the separate `aur-install` skill.

## Clean up
```bash
cd ~/aur/<pkgname>
git clean -dfx
```
