---
name: contribute-skill
description: Guide for adding new skills or contributing to the domovoy-skills public repository. Covers skill conventions (frontmatter, naming, tiers), the store/fridge model, contribution workflow, leaf patterns for browser migration, per-datatype formats, and the review checklist. Use when creating a new skill or updating an existing one for the public repo.
license: GPL-3.0-or-later
compatibility: opencode
metadata:
  family: contributing
  topic: skills
---

# contribute-skill

How to add a new skill to the [domovoy-skills](https://github.com/alexindigo/domovoy-skills)
public repository — the open-source **store** for Domovoy skills.

## The store/fridge model

```
  domovoy-skills repo     = the store (canonical, public, version-controlled)
  local clone             = the farmer's market (your copy of the store)
  ~/.agents/skills/       = the fridge (what the agent loads at runtime)
```

Skills flow: **store → local clone → fridge.** When you create a new skill,
develop and test it in the fridge first, then publish it to the store by copying
it into the local clone and committing. The fridge may also hold private/
machine-specific skills that never go to the store.

---

## Design principles

### Delegate, don't duplicate

When a skill covers a broad topic (e.g. model exploration), extract narrow
reusable pieces into their own skills (e.g. model downloading). The broader
skill **delegates** to the narrower one rather than repeating its content.

```
model-explorer  ──►  hf-model-download   (download mechanics, single source of truth)
                 ──►  model-explorer     (discovery, budgeting, testing — only here)
```

The narrow skill is the **single source of truth** for its mechanics. If it
improves (new curl flags, better error handling), every skill that delegates to
it benefits — no edits needed. The delegating skill says "load skill X for the
download step" and keeps only a one-line summary for context.

When to extract:
- You find yourself copy-pasting the same steps across multiple skills.
- A piece is useful on its own (e.g. "just download a model" vs. "explore the HF
  model landscape").
- A piece might evolve independently (token handling, authentication flows).

When to keep inline:
- The steps are specific to the delegating skill's workflow (e.g. model-explorer's
  VRAM budgeting is its own concern, not hf-model-download's).
- The piece is trivial (2-3 lines) and extracting it adds more indirection than
  value.

### `metadata` records the relationship

```yaml
metadata:
  related: hf-model-download
```

This is advisory — opencode's flat-skill discovery doesn't enforce hierarchy.
But future tooling or contributors can trace the delegation graph.

---

## Skill file structure

Each skill is ONE directory with a `SKILL.md` (required) and optional scripts:

```
skill-name/
  SKILL.md          ← required, with valid frontmatter
  extract.py        ← optional: extraction/injection script
  FORMAT.md         ← optional: a data-format spec the skill defines
  README            ← optional: any other supporting file
```

No `__pycache__/`, `.pyc` files, `.stfolder/` markers, or `.git` dirs should
ever be published. Scripts are language-agnostic — pick the best runtime per
skill (Python, POSIX sh, etc.) and state the choice in SKILL.md.

---

## Naming conventions

Skill name = directory name = `name` in frontmatter. Rules (enforced by opencode):

- **Lowercase alphanumeric, single hyphens:** `^[a-z0-9]+(-[a-z0-9]+)*$`
- 1–64 characters, must not start or end with `-`.
- Must be **unique** in the store.

### Name patterns (by category)

| Category | Pattern | Example |
|----------|---------|---------|
| Migration orchestrator | `user-migration-<direction>` | `user-migration-source` |
| Datatype logic (migration) | `browser-<datatype>-<direction>` | `browser-bookmarks-source` |
| Browser extraction leaf | `<browser>-<datatype>-extraction` | `firefox-bookmarks-extraction` |
| Browser injection leaf | `<browser>-<datatype>-injection` | `brave-bookmarks-injection` |
| Non-browser sink | `<endpoint>-<datatype>-target` | `linkwarden-bookmarks-target` |
| Infrastructure | `<topic>-setup` or `topic-<verb>` | `syncthing-setup`, `git-repo-identity` |
| Contributing / meta | `contribute-<thing>` | `contribute-skill` |

### Tiers (for migration skills)

A migration skill may be an **orchestrator**, a **logic** skill, or a **leaf**.
This is recorded in `metadata.tier`:

- `orchestrator` — top-level entry point (invoked by the user/other agent)
- `logic` — datatype logic (owns a format, dispatches to leaves)
- `leaf` — browser/endpoint mechanics (extracts from or injects into ONE target)

The hierarchy is **logical** (naming + metadata) because opencode discovers
skills flat, not nested.

---

## Frontmatter (required)

Every `SKILL.md` must start with YAML frontmatter:

```yaml
---
name: contribute-skill
description: A short description (1-1024 chars). Include WHEN to use this skill.
license: GPL-3.0-or-later
compatibility: opencode
metadata:
  family: <logical-group>      # e.g. user-migration, infrastructure, contributing
  topic: <brief-tag>
  tier: <orchestrator|logic|leaf>   # for migration skills
  parent: <parent-skill-name>        # if this is a leaf, who calls it
  datatype: <bookmarks|tabs|...>     # for datatype logic/leaf skills
  direction: <source|target>
  browser: <browser-id>              # for browser leaves
  leaf_pattern: <pattern>            # expected leaf name pattern
---
```

Key fields:
- **`name`** (required) — must match the directory name exactly.
- **`description`** (required) — 1–1024 chars. Be specific about WHEN to use the skill (not just WHAT it does). Include hint phrases like "Use on the SOURCE machine when migrating" or "Use when creating a new git repo."
- **`license`** — for the store, always `GPL-3.0-or-later`.
- **`compatibility`** — `opencode` (the runtime).
- **`metadata`** — used to encode the logical hierarchy since skills are flat-dir. All fields optional.

---

## Creating a new skill (workflow)

### 1. Develop in the fridge
```bash
mkdir ~/.agents/skills/<skill-name>
# write SKILL.md with frontmatter
# add scripts if needed (chmod +x if executable)
```
Test the skill locally — invoke it via opencode, refine, iterate.

### 2. Validate frontmatter
```python
# Check name matches dir, regex, description length
import re, yaml
nr = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
t = open('SKILL.md').read()
fm = t.split('---\n', 2)[1]
d = yaml.safe_load(fm)
assert d['name'] == dirname and nr.match(d['name'])
assert 1 <= len(d['description']) <= 1024
```

### 3. Review for leaks
- No personal info: emails, names, hostnames, IPs, tokens.
- Machine-agnostic paths (use `~/`, `$HOME`, `<home>`, not `/home/<user>`).
- If a skill references infrastructure (e.g. `search.home`), document it
  as a user-configurable setting in the skill prose or README.

### 4. Copy to the store and commit
```bash
cp -r ~/.agents/skills/<skill-name> ~/Public/domovoy-skills/<skill-name>
cd ~/Public/domovoy-skills
git add <skill-name>/
git commit -m "<descriptive message>"
git push origin master
```
Omit `__pycache__/`, `.git/`, `.stfolder/` — use `rsync` or `cp -r --excluding`
patterns. The store has `.git/allowed_signers` for local verification.

---

## Per-browser leaf pattern (migration skills)

The migration framework is the flagship example. Adding a new browser follows a
fixed per-leaf convention:

### Extraction leaf
- **Name:** `<browser>-<datatype>-extraction`
- **Depends on:** the datatype format (e.g. `browser-bookmarks-source/FORMAT.md`)
- **Produces:** one JSON file per profile in the shared url-groups format
- **Is called by:** the parent logic skill (e.g. `browser-bookmarks-source`)
- **Example:** `firefox-bookmarks-extraction` reads `places.sqlite` → url-groups
  JSON

### Injection leaf
- **Name:** `<browser>-<datatype>-injection`
- **Consumes:** the url-groups format
- **Writes:** into ONE browser's data store (non-destructive, additive)
- **Is called by:** the target-side logic skill (e.g. `browser-bookmarks-target`)

### Sink (non-browser consumer)
- **Name:** `<endpoint>-<datatype>-target`
- **Consumes:** the same url-groups format
- **Target:** Linkwarden, a plain list, or any non-browser endpoint
- **Example:** `linkwarden-bookmarks-target`

A contributor adding Vivaldi bookmarks creates `vivaldi-bookmarks-extraction`
conforming to the bookmarks format — everything else is reusable. The datatype
logic skills route groups to any destination; the format is the only contract
a leaf must satisfy.

---

## Contribution checklist

Before committing to the store, verify:

- [ ] Frontmatter: `name` == dir, regex-valid, `description` 1–1024 chars
- [ ] No personal info (emails, names, hostnames, IPs, tokens)
- [ ] Machine-agnostic paths (use `~/`, `$HOME`, `<placeholder>`, not real paths)
- [ ] No `__pycache__/`, `.pyc`, `.git/`, `.stfolder/` in the commit
- [ ] Scripts (`.py`/`.sh`) are `py_compile`-clean or `sh -n`-clean
- [ ] Works in the fridge (tested by loading the skill in opencode)
- [ ] If it's a migration skill: conforms to the url-groups format (FORMDAT.md)
- [ ] If it's a browser leaf: `metadata.parent` + `metadata.browser` set correctly
- [ ] License compatible with GPL-3.0-or-later (the store license)
- [ ] Commit message describes the skill and its purpose

Base directory: file:///home/domovoy/.agents/skills/contribute-skill
