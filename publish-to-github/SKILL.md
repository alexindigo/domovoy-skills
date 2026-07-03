---
name: publish-to-github
description: Prepare and push a signed commit to a Domovoy public GitHub repo with a pre-push leak check. Greps staged changes for infrastructure values (LAN subnets, service URLs, device IDs, private ports) that belong in ENVIRONMENT.md instead. Use BEFORE every push to domovoy-bootstrap or domovoy-skills.
license: GPL-3.0-or-later
compatibility: opencode
metadata:
  family: contributing
  topic: git
---

# publish-to-github

Push a signed commit to a Domovoy public repo — with a pre-push leak check.
**Always run the check before pushing.** A single `10.4.0.0/16` or
`search.home` in a public doc exposes your household infrastructure.

---

## 1. Pre-push leak check (mandatory)

Before every push, grep staged changes for infrastructure values:

```bash
cd ~/Public/domovoy-bootstrap   # or domovoy-skills
git diff --cached | grep -iE \
  '10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|\.home\b|\.lan\b|\.local\b' \
  && echo 'LEAK: LAN addresses or internal domains' || echo 'clean: LAN'

git diff --cached | grep -iE \
  'LQTSK7I|[A-Z0-9]{7}-[A-Z0-9]{7}' \
  && echo 'LEAK: Syncthing device IDs' || echo 'clean: device IDs'

git diff --cached | grep -iE \
  'search\.home|searxng|:22013|:22000|:8384|:4096' \
  && echo 'LEAK: service URLs or non-standard ports' || echo 'clean: services'
```

If ANY check fires, **stop.** Replace the leaked value with a placeholder
(`<lan-subnet>`, `<searxng-url>`, `<sync-port>`) or reference
`setup/<hostname>/ENVIRONMENT.md` instead. Amend the commit and re-run the
check.

### What's a leak (never in public files)

| Pattern | Example | Goes in |
|---------|---------|---------|
| LAN subnet / IP | `10.4.0.0/16`, `192.168.1.0/24` | `ENVIRONMENT.md` |
| Internal domain | `search.home`, `*.lan`, `*.local` | `ENVIRONMENT.md` |
| Service URLs | `http://search.home/` | `ENVIRONMENT.md` |
| Non-standard ports | `:22013`, `:4096` | `ENVIRONMENT.md` (or generic `:8080` is fine — it's a common default) |
| Syncthing device IDs | `LQTSK7I-...` | `ENVIRONMENT.md` |
| Hardware serial numbers | — | Never in any file |

### What's safe (ok in public files)

| Pattern | Why safe |
|---------|----------|
| `github.com/alexindigo/domovoy-*` | Project URLs — self-referencing is correct |
| `localhost`, `127.0.0.1` | Standard loopback — not infrastructure |
| `:8080`, `:8384`, `:22` | Default ports — not specific to any setup |
| Hugging Face repo names | Public model repos — not infrastructure |
| `<placeholder>` or `<example>` | Explicitly generic |

---

## 2. Where infrastructure values belong

`setup/<hostname>/ENVIRONMENT.md` — Syncthing-synced, fleet-only, **never
committed to a public repo.** Skills reference it; public docs use
placeholders.

```
ENVIRONMENT.md (private, fleet-synced)
  ├── Network: LAN subnet, DNS suffix
  ├── Services: SearXNG URL
  └── Syncthing: hub device ID, hub name
```

See the `system-info` skill for the full convention.

---

## 3. Commit and push

Once the leak check passes:

```bash
git add <files>
git commit -S -m "<message>"   # -S signs with domovoy's SSH key
git push origin master
```

Verify the signature:
```bash
git log --show-signature -1    # "Good signature for ...@domovoy"
```

If the commit comes out unsigned (known git 2.54 quirk):
```bash
git commit --amend -S --no-edit   # re-sign
```

---

## 4. Amending leaked commits (damage control)

If a leak was already pushed:

1. Fix the file (replace values with placeholders).
2. `git add <file> && git commit --amend -S --no-edit`
3. `git push --force origin master`

Force push requires **explicit user approval** — never do it silently.
It rewrites public history and can disrupt collaborators who pulled the
old commit.

### After the force push

The leaked commit is no longer reachable from `master`. GitHub garbage-
collects unreachable objects eventually. The only protection is the leak
check in step 1 — do it **before** pushing, not after.

---

## 5. Domovoy's commit identity

Per the `git-repo-identity` skill, each Domovoy uses its own SSH key and a
fingerprint-derived email:

```
user.name  = "Domovoy"
user.email = "<8-hex-chars>@domovoy"  # first 8 chars of ssh-keygen -lf ~/.ssh/id_domovoy.pub
```

The email is unique per machine without leaking topology. The commit is
signed with `~/.ssh/id_domovoy`. Local verification via `.git/allowed_signers`.

Base directory: file:///home/domovoy/.agents/skills/publish-to-github
