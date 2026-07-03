# Skill: system-documentation

# System Documentation

Maintain four documents per machine, each serving a distinct role. Know what goes where.

## Four-document system

### 1. SYSTEM_INFO.md — the snapshot

Location: `setup/<hostname>/SYSTEM_INFO.md`

**Purpose:** Dictionary of what the machine IS right now. Immutable traits + current state values. Quick lookup — "What CPU does this host have?"

**Content:**
- Hostname
- Hardware: CPU, RAM, GPU, storage devices, boot type (UEFI/BIOS)
- Disk layout: partitions, filesystems, mount points, LUKS, btrfs subvolumes
- Current kernel version
- Current kernel parameters
- Architecture-specific notes (GPU driver quirks, hardware bugs, firmware notes)

**Style:** Present tense, declarative. `CPU: Intel Core Ultra 9 285HX`. Not "we installed."

**Update when:** Physical hardware changes, kernel updates, storage layout changes.

### 2. SYSTEM_SETUP.md — the blueprint

Location: `setup/<hostname>/SYSTEM_SETUP.md`

**Purpose:** Golden-path instructions to rebuild this machine from scratch. Step-by-step, imperative — "do this, then that." Only includes what actually works and stays. No dead ends, no "tried X and reverted." That's what reports are for.

**Content (in order of execution):**
- Partitioning commands (sgdisk, cryptsetup, mkfs)
- Subvolume creation
- pacstrap/bootstrap
- Initramfs configuration
- Bootloader installation and config
- Package lists (official + AUR) with purposes
- User creation
- Post-install configuration: services, config files, timers
- Architecture-specific notes (pci=noats, fbcon considerations)

**Style:** Imperative, present tense. `Add pci=noats to suppress ACSViol errors.` Not "we added pci=noats after seeing 9k errors."

**Update when:** New permanent packages, config changes, services enabled, new setup steps. Every permanent state change should be reflected as a step in this document.

### 3. Maintenance reports — the binlog

Location: `maintenance/reports/YYYY-MM-DD.md`

**Purpose:** Append-only chronological log of every state-changing action. The complete history — warts, reversals, dead ends. If something breaks, trace backwards through the binlog.

See `maintenance-report` skill for format and rules.

**Content:** Every command that changes state, with why, what was done, and result. Failed attempts and reversals included.

**Style:** Past tense. `Ran snapper create-config. Failed — path mismatch. Reverted.`

**Update when:** IMMEDIATELY after every state-changing command, subtask, or logical step. Never batch. Log failures too.

### 4. ENVIRONMENT.md — the service config

Location: `setup/<hostname>/ENVIRONMENT.md`

**Purpose:** Machine-specific infrastructure settings — service URLs, network
config, Syncthing hub — that skills should **reference** rather than hardcode.
Read by the `system-info` skill at session start; populated during bootstrap.

**Content:**
- Network: LAN subnet, DNS suffix
- Services: SearXNG URL, any household-specific service endpoints
- Syncthing: hub device ID and name

**Style:** Key-value in Markdown tables. One table per category.

**Not in ENVIRONMENT:** Hardware specs (SYSTEM_INFO), rebuild instructions
(SYSTEM_SETUP), command logs (reports). No secrets (those go in env vars or
auth files).

**Never published to public repos.** ENVIRONMENT.md is fleet-synced via
Syncthing only.

## Document boundaries

| Question | Goes in |
|----------|---------|
| What CPU does this machine have? | SYSTEM_INFO.md |
| How do I set up btrfs subvolumes? | SYSTEM_SETUP.md |
| Why did we choose Limine over GRUB? | SYSTEM_SETUP.md (explain in context) |
| What did we try that failed? | reports/ (not SYSTEM_SETUP.md) |
| When was snapper installed? | reports/YYYY-MM-DD.md |
| What's the current kernel version? | SYSTEM_INFO.md |
| How do I blacklist iTCO_wdt? | SYSTEM_SETUP.md |
| Where is the SearXNG instance? | ENVIRONMENT.md |
| What's this household's LAN subnet? | ENVIRONMENT.md |
| What's the Syncthing hub device ID? | ENVIRONMENT.md |
| Did vt.global_cursor_default=0 work? | reports/ (no, doesn't belong in setup) |

## When to update which

| Trigger | Update |
|---------|--------|
| Package installed/removed | SYSTEM_SETUP.md + report |
| Config file changed | SYSTEM_SETUP.md + report |
| Service enabled/disabled | SYSTEM_SETUP.md + report |
| Kernel updated | SYSTEM_INFO.md + report |
| Hardware changed | SYSTEM_INFO.md + report |
| Failed experiment | report only |
| Reverted change | report only |
| Documentation/rule change | AGENTS.md + report |

## Cross-machine context

`setup/<hostname>/` is synced across machines via Syncthing. The domovoy on machine A can read machine B's documents to:

- Understand what hardware/packages B has (SYSTEM_INFO.md)
- Learn how B was set up (SYSTEM_SETUP.md)
- Apply patterns from B that make sense for A
- See what configurations are common vs machine-specific
