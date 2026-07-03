---
name: configure-local-models
description: Configure opencode to use local llama.cpp models. Writes the provider, lists model IDs from a running llama-server API, sets per-agent model routing (build/plan/explore), and maps the small_model for background tasks. Use AFTER downloading models (hf-model-download) and starting the llama-server service. For discovering new models, use model-explorer first.
license: GPL-3.0-or-later
compatibility: opencode
metadata:
  family: infrastructure
  topic: models
  related: [hf-model-download, model-explorer]
---

# configure-local-models

Wire a running llama-server's models into opencode's config so the agent can
use them. This is the **last step** after downloading models
(`hf-model-download`) and starting the llama-server service. For discovering
and evaluating models, use `model-explorer` first.

---

## 1. Verify the llama-server is running

```bash
curl -s http://localhost:8080/v1/models | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f'{len(d[\"data\"])} models available')
"
```

If nothing responds, the server isn't running. Check:
```bash
systemctl --user is-active llama-server.service
```

---

## 2. Write the provider config

opencode has a **built-in `llama.cpp` provider** — no custom provider hackery
needed. Add to `~/.config/opencode/opencode.jsonc`:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "llama.cpp": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "llama-server (local)",
      "options": {
        "baseURL": "http://127.0.0.1:8080/v1"
      },
      "models": {
        "granite-4.1-8b-Q4_K_M": { "name": "Granite 4.1 8B (Fast)" }
        // add a model entry for each model in the pool
      }
    }
  }
}
```

### Model IDs

The model IDs must **exactly match** the `id` field returned by
`GET /v1/models`. That is the GGUF filename without `.gguf`. Run:

```bash
curl -s http://localhost:8080/v1/models | python3 -c "
import sys,json
d=json.load(sys.stdin)
for m in d['data']:
    print(f'  {m[\"id\"]}')
"
```

Copy each ID into the `models` map with a human-readable `name`.

### baseURL note

Use `127.0.0.1` (local loopback) even if the llama-server also listens on
`0.0.0.0`. opencode runs on the same machine — localhost is correct and avoids
routing through the firewall unnecessarily.

---

## 3. Per-agent model routing

Map models to opencode's built-in agents:

```jsonc
{
  "model": "llama.cpp/gemma-4-12b-it-Q4_K_M",       // default = build
  "small_model": "llama.cpp/granite-4.1-8b-Q4_K_M",  // titles, summaries
  "agent": {
    "build": {
      "model": "llama.cpp/gemma-4-12b-it-Q4_K_M"    // Daily driver
    },
    "plan": {
      "model": "llama.cpp/deepseek-r1-distill-qwen-14b-Q4_K_M"  // Think
    },
    "explore": {
      "model": "llama.cpp/granite-4.1-8b-Q4_K_M"    // Fast
    }
  }
}
```

- **build** — the default agent. Uses your Daily model.
- **plan** — analysis, investigation, debugging. Uses Think.
- **explore** — codebase search, data gathering. Uses Fast.
- **small_model** — lightweight background tasks (title generation, summaries).

The format for a model reference is `llama.cpp/<model-id>` — the provider key
combined with the model ID from your `models` map.

A model reference is optional for any agent; if omitted, the agent inherits
from the top-level `model`. Use `/models` in the opencode UI to switch models
interactively.

---

## 4. Swap models without restart

Edit `opencode.jsonc`, change the `model` value for any agent, save.
opencode picks up the change on the next request. The llama-server never needs
a restart — it auto-loads the requested model on first use.

---

## 5. Full workflow recap

```
model-explorer        → discover models, evaluate community adoption
hf-model-download     → download selected GGUF files to ~/models/
llama-server start    → systemctl --user restart llama-server.service
configure-local-models → write opencode.jsonc (this skill)
/models               → verify models appear in the picker
```

---

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Model not in `/models` picker | ID in config doesn't match API | Compare against `GET /v1/models` — exact match required |
| opencode ignores config | JSONC syntax error | Check braces match; remove trailing commas in objects |
| "Loading model" timeout | Model is loading from disk for first time | Wait — large models take 10-30s to load; subsequent prompts are fast |
| Tool calls failing | Model doesn't support tool calling well | Try Qwen or Gemma variants; Granite excels at tool calling |

Base directory: file:///home/domovoy/.agents/skills/configure-local-models
