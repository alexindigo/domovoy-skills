# Skill: system-info

# SYSTEM_INFO.md — Creation and Maintenance

Keep `setup/<hostname>/SYSTEM_INFO.md` complete and current for every machine the domovoy lives on.

## What SYSTEM_INFO.md IS

A machine-specific dictionary of immutable and quasi-immutable facts. Quick lookup — "What CPU does this host have?" "What GPU driver?" "What's the current kernel?"

Answers "what IS the machine right now" — not "how was it built" (that's SYSTEM_SETUP.md) and not "what did we do" (that's maintenance reports).

## When to populate (new machine bootstrap)

When onboarding a new machine, populate SYSTEM_INFO.md immediately from live system data. Gather:

### Hardware
```bash
hostname
lscpu | grep 'Model name' | head -1
free -h | grep Mem
lspci | grep -i vga
lspci -nn | grep -i '8086'  # Intel devices
```

### When local tools can't determine specs

Some hardware (especially GPUs on newer kernel drivers like `xe`) doesn't expose
full specs through sysfs, `lspci -v`, or monitoring tools. When local commands
return incomplete data:

1. Search the internet for the product's official specifications
2. Preferred sources: **Wikipedia** (GPU comparison tables), **manufacturer ARK/product pages**
3. Verify with multiple sources if possible
4. Document what you find alongside the PCI ID
5. For GPUs: capture VRAM, bus width, core count, clock speeds, TDP, and PCIe generation
6. Example: Arc Pro B50 — `lspci` showed `8086:E212`, but VRAM was only found via Wikipedia (16 GB GDDR6)

This applies to any hardware where the driver doesn't expose full specs — NICs, RAID controllers, etc.

### Storage
```bash
lsblk -o NAME,UUID,FSTYPE,SIZE,MOUNTPOINT
btrfs subvolume list /
findmnt -t btrfs
```

### Boot
```bash
bootctl status 2>/dev/null   # bootloader, firmware
efibootmgr                    # EFI boot entries + order
uname -r                      # kernel version
```

### Packages
```bash
pacman -Q | wc -l              # total packages
pacman -Q intel-compute-runtime 2>/dev/null  # key versions
```

### Networking
```bash
# active interfaces with IPs, subnets, and state
ip -br addr | grep -v LOOPBACK | grep -v 'DOWN'
# default gateway
ip route | grep default
# DNS search domain (the .home / .local suffix convention)
grep -i '^search' /etc/resolv.conf 2>/dev/null || true
```
Record the LAN subnet (CIDR) explicitly — this is used to auto-discover firewall
scope for services that should be LAN-accessible. Also list known LAN services
(SearXNG, Syncthing, etc.) so the agent knows the machine's network context.

## When to update

| Trigger | What to update |
|---------|---------------|
| Kernel update | Kernel version line |
| Package install/remove | Package count (or notable packages) |
| GPU driver change | GPU line, compute section |
| Hardware change | Hardware table |
| Storage layout change | Storage section |
| New network interface | Networking list |
| IP/subnet/DNS change | Networking section |
| New LAN service | Networking section |
| Boot config change | Boot section, kernel parameters |

## What NOT to put here

- **Don't** put build instructions — those go in SYSTEM_SETUP.md
- **Don't** put session logs — those go in maintenance reports
- **Don't** put trial-and-error history — reports only
- **Don't** put detailed rationale (e.g., "why we chose LZO over LZ4") — rationale notes are fine, but full history goes in reports

## File structure

```markdown
# System Profile — <hostname>

## Hardware
| Component | Detail |
|-----------|--------|
| **Hostname** | ... |
| **CPU** | ... |
| **RAM** | ... |
| **GPU** | ... (include driver, architecture, PCI ID, VRAM if known) |
| **Storage** | ... |

## Storage Layout
(partition tables, subvolumes, mount points)

## Boot
(bootloader, kernel, microcode, mirror setup)

## OS
(distribution, kernel version, package count)

### GPU Compute
(compute runtime, drivers, notable AI/ML packages)

## Networking
- `<iface>` (active): `<ip>/<cidr>` — wired/wireless, LAN subnet `<subnet>`, DNS suffix `<domain>`
- Default gateway: `<ip>`
- LAN services: SearXNG (`search.home:80`), Syncthing NAS (`storage`), etc.

## Users
(human and service accounts)

## Storage Conventions
(any directory conventions like ~/Packages/ or ~/aur/)
```

## Cross-machine context

Since `setup/<hostname>/` is synced via Syncthing, other domovoy instances can read this file to learn about this machine's hardware and capabilities. The domovoy on machine A might see that machine B has an Intel Arc GPU and know it can run local AI models there.
