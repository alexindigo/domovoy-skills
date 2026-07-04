---
name: git-repo-identity
description: Set up per-repository git identity with SSH commit signing and local signature verification — everything in .git/config and .git/, nothing global. For users with multiple git identities across repos. Covers the open-key temporary workaround and the path to passphrase-protected keys via ssh-agent / 1Password broker. Use when Cloning or creating a new repo that needs its own signing identity.
license: GPL-3.0-or-later
compatibility: opencode
metadata:
  family: infrastructure
  topic: git
---

# git-repo-identity

Set up **per-repository** git author identity, SSH commit signing, and local
signature verification — everything scoped to `.git/config` + `.git/`, nothing
in global config. Designed for people who use **multiple git identities** across
repos and never want one repo's identity to leak into another.

---

## The model

```
  repo-a/.git/config  ← author + signing for identity A
  repo-b/.git/config  ← author + signing for identity B
  ~/.gitconfig        ← empty or unrelated (NO identity leaking between repos)
```

Everything is per-repo:
- **Author** (`user.name`, `user.email`)
- **Signing** (SSH format, key path, auto-sign commits/tags)
- **Verification** (`allowedSignersFile` → `.git/allowed_signers` inside the repo)

---

## Quick setup (copy-paste snippet)

Given an existing **SSH key pair** (with the public key already on GitHub as a
**Signing key**) and the identity you want for this repo:

```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
KEY_NAME="id_ed25519_example"        # name of your key in ~/.ssh/

# 1. Author identity
git config user.name  "Your Name"
git config user.email "your@email.example"

# 2. SSH signing (uses the PUBLIC key path)
git config gpg.format ssh
git config user.signingkey "$HOME/.ssh/${KEY_NAME}.pub"
git config commit.gpgsign true
git config tag.gpgsign true

# 3. Local verification (per-repo allowed_signers in .git/)
echo "your@email.example $(cat "$HOME/.ssh/${KEY_NAME}.pub")" \
  > "$REPO_ROOT/.git/allowed_signers"
git config gpg.ssh.allowedSignersFile .git/allowed_signers

# 4. Verify it works
git verify-commit HEAD
```
The above assumes the private key is **unencrypted** (open key — see below).
For passphrase-protected keys, see §SSH Agent / 1Password Broker.

On git 2.54+ you can alternatively write `git config set --local …`.

---

## What each piece does

### Author identity (per-repo)
`git config user.name` / `user.email` write to `.git/config` (default without
`--global`). This overrides anything in `~/.gitconfig` for this repo only.

### SSH commit signing
- `gpg.format ssh` — git uses SSH keys (not GPG) to sign commits.
- `user.signingkey` points at the **public key** file (git signs with the
  corresponding private key — same filename without `.pub`, or from an agent).
- `commit.gpgsign true` — every `git commit` auto-signs. `git commit --no-gpg-sign`
  skips signing for a one-off.
- `tag.gpgsign true` — same for annotated tags (optional; de-sign with
  `--no-gpg-sign`).

### Local verification (`.git/allowed_signers`)
`gpg.ssh.allowedSignersFile .git/allowed_signers` points at a simple file:

```
your@email.example ssh-ed25519 AAAAC3...comment
```

One line per signer email + key. The file lives in the non-version-controlled
`.git/` dir, so it is **local-only** (never pushed) and travels with the repo on
this machine. An absolute path also works; the relative `.git/allowed_signers`
resolves from the repo's worktree root (confirmed on git 2.54).

---

## SSH keys: open-key (temporary) → agent (future)

### Current: open key (temporary workaround)

If your SSH private key is **unencrypted** (no passphrase), git reads it directly
from `~/.ssh/<name>` (matching the pubkey in `user.signingkey`). Signing works
non-interactively — the domovoy agent can sign commits on your behalf.
This is a **temporary convenience**; treat an unencrypted private key the same
way you treat a plaintext password — and migrate off it when feasible.

### Future: passphrase-protected key via ssh-agent (the goal)

When your key is passphrase-protected:

1. Add it to ssh-agent: `ssh-add ~/.ssh/<private-key>`
2. Set `SSH_AUTH_SOCK` in your environment (ssh-agent does this).
3. Git signing now works via the agent — no open key needed.

From a **non-interactive context** (like the domovoy agent signing as you):

```
sudo -u <user> SSH_AUTH_SOCK=<path> git -C <repo> commit -S -m "msg"
```

Without the agent, signing with a passphrase-protected key will hang prompting
for the passphrase (which is unreachable non-interactively) or fail.

### 1Password SSH Broker (the ideal)

1Password can serve as an SSH agent, holding the passphrase-protected key and
exposing an `SSH_AUTH_SOCK`. Once configured, git signing "just works" in both
interactive and agent contexts. The domovoy agent respects the same
`SSH_AUTH_SOCK` path.

Setup reference phrases (the agent should confirm details with the user and
1Password docs, as the setup UX varies by platform):
- Enable 1Password SSH agent in 1Password settings.
- Export `SSH_AUTH_SOCK` to point at the 1Password agent socket.
- `ssh-add -L` should list the loaded keys.
- Git signing config is **unchanged** from above — the agent handles the
  passphrase transparently.

When this is working, the open-key workaround is no longer needed and the
private key can be regenerated with a passphrase.

---

## GitHub "Verified" badge

After setup, push a signed commit. GitHub shows **Verified** if:
1. The commit is signed (SSH signature present).
2. The **signing public key** is registered on GitHub at
   **Settings → SSH and GPG keys → SSH Signing Keys** (NOT Authentication Keys).
3. The email in the commit matches a verified email on your GitHub account.

The local `allowedSignersFile` and the GitHub SSH signing key are **independent** —
one ensures local `verify-commit` passes, the other ensures the web badge.

---

## Setup from scratch (no key yet)

If no SSH key exists:
```bash
ssh-keygen -t ed25519 -C "your@email.example" -f ~/.ssh/id_ed25519_<purpose>
```
- If using the open-key workaround: press Enter at the passphrase prompt (no
  passphrase). Know the tradeoff.
- If using an agent/1Password: set a strong passphrase.

Then upload the `.pub` file to GitHub as a **Signing Key**.

---

## Verify the setup

```bash
git log --show-signature -1   # "Good signature for your@email.example"
git verify-commit HEAD        # same, programmatic
git config --local --list | grep -E 'user\.|gpg\.|commit\.gpg'  # confirm local-only
```

---

## Gotchas

- **First commit may come out unsigned** even with `commit.gpgsign=true` — a
  known quirk in git 2.54. If it happens, `git commit --amend -S --no-edit` fixes
  it (and re-signs). The second commit onward signs cleanly.
- **Relative vs absolute path:** `.git/allowed_signers` resolves from the repo
  worktree root (confirmed on git 2.54). If your version behaves differently,
  use the absolute path instead.
- **`visudo`-stye permission errors:** if `.git/allowed_signers` is unreadable by
  the committing user, `--show-signature` just says "No signature" with no
  explanation — check perms.
- **LLM trap: never type a key by hand.** SSH public keys are base64 blobs.
  LLMs systematically hallucinate key text when typing from memory. Always
  read from disk — `cat ~/.ssh/<key>.pub` — in the same tool call as the
  message that displays it. Never copy-paste a key from your own previous
  output; re-reading from disk is idempotent and safe. If you need to verify
  the key matches what was previously shown, compare fingerprints with
  `ssh-keygen -lf`, not the base64 text.

Base directory: file:///home/domovoy/.agents/skills/git-repo-identity
