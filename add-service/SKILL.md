---
name: add-service
description: Add a service's port to nftables with an interactive LAN-accessibility prompt. Reads the LAN subnet from setup/<hostname>/ENVIRONMENT.md, inserts the rule before the reject catch-all, and persists to /etc/nftables.conf. Also flags if the service binds to 127.0.0.1 only and needs a config change. Use when a new service needs firewall access — one service per invocation.
license: GPL-3.0-or-later
compatibility: opencode
metadata:
  family: infrastructure
  topic: firewall
  related: [system-info]
---

# add-service

Add a service's port to nftables with a LAN-accessibility prompt. Handles the
common bottleneck (firewall) and flags binding issues. Does NOT edit service
configs itself — tells the Domovoy what else needs changing.

## 1. Discover the service

Ask the user for the **service name** and **port**. Determine the current
listening address:

```bash
ss -tlnp 2>/dev/null | grep ":<port>"
```

- If `127.0.0.1:<port>` — the service binds localhost-only. LAN access needs
  BOTH a firewall rule AND a binding change in the service config.
- If `0.0.0.0:<port>` or `*:<port>` — already bound to all interfaces. Only
  the firewall rule is needed.

## 2. Ask about LAN accessibility

```
"Should <service> be accessible from the LAN?"
→ yes → add nftables rule
→ no  → stop here
```

**Never** expose a service without asking. Per Domovoy safety rules, even
`127.0.0.1` could be reachable from the internet via tunnels or forwarding.

## 3. Read the LAN subnet

From `setup/<hostname>/ENVIRONMENT.md` → `Network → LAN subnet`. This is
the CIDR the rule will restrict to (e.g. `10.4.0.0/16`). If ENVIRONMENT.md
doesn't have it, fall back to `ip -br addr | grep UP` to find the active
interface subnet.

## 4. Add the firewall rule (before reject)

```bash
# Find the position just before the reject meta rule
POS=$(sudo nft -a list chain inet filter input 2>/dev/null | grep 'reject with icmpx' | awk '{print $NF}')
sudo nft add rule inet filter input position $((POS - 1)) ip saddr <subnet> tcp dport <port> accept comment "allow <service> from LAN"
```

The rule MUST go **before** the reject catch-all at the end of the chain.
Appending after the reject makes the rule unreachable. Insert it just above
the reject — the existing LAN rules (8384, 8080, 4096) follow this pattern.

## 5. Persist to nftables.conf

```bash
sudo sed -i "/^    pkttype host.*reject with icmpx/i\    ip saddr <subnet> tcp dport <port> accept comment \"allow <service> from LAN\"" /etc/nftables.conf
```

Verify:
```bash
grep "<port>" /etc/nftables.conf
```

## 6. Verify

```bash
ss -tlnp 2>/dev/null | grep "<port>"
curl -s http://<lan-ip>:<port>/ 2>/dev/null | head -1
```

## 7. Flag binding changes

If the service binds to `127.0.0.1` only, tell the Domovoy: "The service
needs its config updated to bind to `0.0.0.0` (or the LAN interface). The
firewall rule alone is not enough — LAN traffic won't reach localhost."
Suggest the likely config file (e.g. Syncthing's `config.xml`, llama-server's
`--host` flag, a systemd `Environment=` directive).

---

## Example: Syncthing GUI

```
Service: Syncthing GUI (user)
Port: 8384
Current binding: 127.0.0.1 → needs config change
LAN? yes

Result:
  - Changed <address>127.0.0.1:8384 → <address>0.0.0.0:8384 in config.xml
  - Added nftables: ip saddr 10.4.0.0/16 dport 8384 accept
  - Persisted to /etc/nftables.conf
```

Base directory: file:///home/domovoy/.agents/skills/add-service
