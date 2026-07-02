---
name: aur-install
description: Use ONLY when installing built AUR packages. Presents the package, checks for conflicts, and installs with pacman -U. Requires explicit user approval.
---

# AUR Package Installation

## Before installing

1. **Verify the package exists** — show the file name, size, and path:
   ```bash
   ls -lh ~/aur/<pkgname>/*.pkg.tar.zst
   ```

2. **Check for conflicts:**
   ```bash
   pacman -Q <pkgname>
   ```

3. **Present to user:**
   ```
   Package: llama.cpp-sycl-f16-server-b9828-1-x86_64.pkg.tar.zst
   Size: 15 MB
   Conflicts: none
   Install?
   ```

4. **Wait for explicit approval.** Never install without go-ahead.

## Install

```bash
sudo pacman -U ~/aur/<pkgname>/<package>.pkg.tar.zst
```

## Verify

```bash
pacman -Q <pkgname>
which llama-server
```

## Clean up

```bash
cd ~/aur/<pkgname>
git clean -dfx
```
