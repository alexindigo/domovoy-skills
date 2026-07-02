# domovoy-skills

Skill library for [Domovoy](https://github.com/alexindigo/domovoy-bootstrap),
a personal sysadmin agent — a household daemon for your machines.

This is the open-source **store** for Domovoy skills. Skills flow from here into
each machine's **fridge** (`~/.agents/skills/`) where the agent loads them at
runtime. The store is canonical; the fridge may hold additional personal/machine-
specific skills never published here.

## Installing a skill

```bash
# clone this repo locally (your "farmer's market")
git clone git@github.com:alexindigo/domovoy-skills.git ~/Projects/domovoy-skills

# copy a skill into the fridge
cp -r ~/Projects/domovoy-skills/<skill-name> ~/.agents/skills/<skill-name>
```

Fridge skills are synced across your fleet via Syncthing. Only copy what you need;
not every machine needs every skill.

## What's inside

### Migration framework (flagship)
A drop-in replacement for Apple's Migration Assistant, rebuilt as cooperating
agent skills. Source packs user data into a portable bundle; target unpacks and
integrates — with bookmarks, open tabs, and interactive routing.

- `user-migration-source`, `user-migration-target` — orchestrators
- `browser-bookmarks-source`, `browser-tabs-source` — datatype logic skills
- `browser-bookmarks-target`, `browser-tabs-target` — merge & routing
- `firefox-bookmarks-extraction`, `chromium-bookmarks-extraction` — per-browser leaves
- Per-browser leaf pattern: `<browser>-<datatype>-extraction|injection`

### Infrastructure
- `git-repo-identity` — per-repo git identity + SSH commit signing + local verification
- `syncthing-setup` — leaf/hub Syncthing architecture with NAS-side versioning

### System
- `system-info`, `system-documentation` — machine-state tracking
- `maintenance-report` — session binlog
- `aur-build`, `aur-install` — AUR package management (Arch Linux)
- `search` — SearXNG-powered local web search (configure your instance)

## Related

- [domovoy-bootstrap](https://github.com/alexindigo/domovoy-bootstrap) — stand up
  a Domovoy on a new machine
- [opencode](https://github.com/anomalyco/opencode) — the agent runtime Domovoy
  lives in

## License

GPL-3.0-or-later
