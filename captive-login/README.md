# captive-login

CLI tool for solving captive WiFi portals without a GUI browser.

Detects captive portals, parses the login form, prompts for fields interactively, submits, and verifies internet access. All from the terminal — no browser needed.

---

## Quick install

```bash
cp captive-login ~/bin/
chmod +x ~/bin/captive-login
```

Make sure `~/bin` is in your `PATH`.

## Dependencies

- **curl** — HTTP requests
- **python3** — URL encoding (usually pre-installed)

That's it. No heavy frameworks, no Node.js, no GUI libraries.

## Usage

```bash
captive-login           # detect portal → interactive login → verify
captive-login --debug   # verbose output
```

### Example

```
$ captive-login
🔍 Checking captive portal...
  Checking http://detectportal.firefox.com/success.txt ...
  ✓ OK (no portal)
✅ No captive portal detected.
```

Behind a hotel portal:

```
$ captive-login
🔍 Checking captive portal...
  Checking http://detectportal.firefox.com/success.txt ...
  ! → redirected to portal
📡 Portal detected!  URL: http://192.168.1.1:8000/login
📝 Detected form fields:
  [hidden]    csrf_token    = 8a3f7b2c (auto)
  ◇ lastname               → Enter your last name: Smith
  ◇ roomnumber             → Enter your room number: 422
  📧 email                 → Enter email (or press Enter for fake): guest.f3a8b2c7@protonmail.com
  ☑ terms                  → (auto-accepted)
  ☐ subscribe              → (auto-unchecked)
📡 Submitting...
✅ Internet access confirmed.
```

---

## How it works

### Detection chain

Each canary URL is checked in order. The first one that returns the expected response means no portal.

1. `http://detectportal.firefox.com/success.txt` — expects "success" (fastest)
2. `http://captive.apple.com/hotspot-detect.html` — expects Success HTML
3. `http://ipv4.icanhazip.com` — raw HTTP, also shows your public IP
4. `http://neverssl.com` — last resort, slower but reliable

If all fail or return unexpected content → portal detected.

### Field handling

| Type | Behavior |
|---|---|
| `hidden` | Auto-filled from HTML, no prompt |
| `submit` / `button` | Skipped during input, auto-submitted after |
| `text` / `tel` / `url` / `number` | Shows label/placeholder, prompts for input |
| `email` | Prompts; empty input generates a fake disposable email |
| `password` | Silent input (no echo) |
| `checkbox` with **accept/agree/terms** | Auto-checked without prompt |
| `checkbox` with **subscribe/optional/offer** | Auto-unchecked without prompt |
| Other `checkbox` | Prompts [Y/n] |
| `radio` | Shows label, prompts for selection |
| `select` | Shows options, prompts for choice |
| `textarea` | Multi-line input (`.` on its own line to finish) |
| No text fields + just a submit button | Auto-submitted without prompting |

### Retry logic

After each submission, the script verifies internet access using the Firefox canary. On failure:
- Shows the HTTP response status
- Asks if you want to retry (up to 3 attempts)
- On max retries or decline, prints debug info (saved HTML path, form fields sent)

---

## What it won't handle

- **JavaScript-heavy portals** — if the portal requires JS to render the form, you need a headless browser (Playwright, Chrome Headless)
- **Social login** — Google/Facebook OAuth portals require a browser
- **HTTPS captive portals** with cert interception — curl will error out on the fake cert

---

## Skill / Agent setup

If you use opencode (AI coding assistant), the `SKILL.md` file can be placed at:

```
~/.config/opencode/skills/captive-login/SKILL.md
```

This makes the tool's usage documentation available to the agent when working on captive portal related tasks.

---

## Files in this package

```
captive-login/
├── captive-login          # the bash script
├── SKILL.md               # agent skill reference
└── README.md              # this file
```
