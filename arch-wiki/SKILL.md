---
name: arch-wiki
description: Use when researching Arch Linux topics, configuration options, packages, or troubleshooting. Check the locally installed arch-wiki-lite first. Only fetch online if the local copy doesn't have the answer.
---

# Arch Wiki Reference

## Local-first rule

**Always check the local wiki first.** The `arch-wiki-lite` package is installed and provides console-searchable wiki content.

## Local search

```bash
wiki-search <term>
```

Examples:
```bash
wiki-search power-profiles-daemon
wiki-search mkinitcpio hooks
wiki-search Plymouth
```

## Local view

`wiki-search <term>` outputs the full page text to stdout. Pipe to `less` for reading:
```bash
wiki-search <term> | less
```

## List available pages

```bash
wiki-search -l | grep <keyword>
```

## Fallback to online

Only use `webfetch` to pull from `wiki.archlinux.org` if:
1. The local `wiki-search` returns nothing relevant
2. The local page is clearly outdated compared to known recent changes
3. You need a page that doesn't exist in the local snapshot
