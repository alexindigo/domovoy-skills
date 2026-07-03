---
name: captive-login
description: CLI tool for solving captive WiFi portals without a GUI browser. Detects captive portals, parses HTML login forms, prompts interactively for fields, submits, and verifies internet access — all from the terminal. Use ONLY when working with captive portal detection, WiFi login automation, or headless network authentication tasks.
license: GPL-3.0-or-later
compatibility: opencode
metadata:
  family: tool
  topic: networking
---

# captive-login

CLI tool for solving captive WiFi portals without a GUI browser.

Located at: `~/.local/bin/captive-login`

## Usage

```bash
captive-login           # detect portal → interactive login → verify
captive-login --debug   # verbose output
```

## Detection chain

Each canary URL checked in order. First match → no portal.

1. `http://detectportal.firefox.com/success.txt` — expects "success"
2. `http://captive.apple.com/hotspot-detect.html` — expects Success HTML
3. `http://ipv4.icanhazip.com` — raw HTTP, also shows public IP
4. `http://neverssl.com` — last resort (slower)

Any failure (redirect, unexpected body, timeout) → portal detected.
The effective URL after redirects becomes the portal URL.

## Form parsing

- Extracts `form action`, `method`, page `title`, all `input`/`select`/`textarea` fields
- Labels via `<label for="...">` or surrounding text before the input

## Field handling

| Type | Behavior |
|---|---|
| `hidden` | Auto-filled from HTML value, no prompt |
| `submit` / `button` | Skipped during input, auto-submitted after |
| `text` / `tel` / `url` / `number` | Shows label/placeholder, prompts for input |
| `email` | Prompts with placeholder; empty → auto-generate fake `guest.<random>@protonmail.com` |
| `password` | Silent input (no echo) |
| `checkbox` with **accept/agree/terms** labels | Auto-checked without prompt |
| `checkbox` with **subscribe/optional/offer** labels | Auto-unchecked without prompt |
| Other `checkbox` | Prompts [Y/n] |
| `radio` | Shows label, prompts for value |
| `select` | Shows numbered options, prompts for choice number |
| `textarea` | Multi-line input (`.` on its own line to finish) |
| No text fields + just submit button | Auto-submitted without prompting |

## Submit & verify

- POST (or GET) form data to form action URL
- Follows redirects, shows HTTP response status
- Verifies with Firefox canary URL
- Success → "Internet access confirmed"
- Failure → asks retry (max 3 attempts), then shows debug info

## Debug info (on max retries or decline)

- Portal URL
- Form action URL and method
- HTTP response status
- List of field/value pairs sent
- Saved HTML at `/tmp/captive-login.html`

## Dependencies

`curl` and `python3` (for URL encoding). Both usually pre-installed.

## What it won't handle

- JavaScript-heavy portals (need headless browser)
- Social login (Google/Facebook OAuth)
- HTTPS captive portals with cert interception
