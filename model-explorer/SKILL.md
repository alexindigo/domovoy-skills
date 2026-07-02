---
name: model-explorer
description: Discover, download, and test GGUF language models for a Domovoy's local llama.cpp model pool. Covers browsing Hugging Face collections, evaluating community adoption, VRAM budgeting per role, zero-dependency curl downloads (with HF token), filename verification gotchas, and testing models against real sysadmin tasks. Use when exploring new models, expanding a model pool, or setting up local inference for the first time.
license: GPL-3.0-or-later
compatibility: opencode
metadata:
  family: infrastructure
  topic: models
  related: DOMOVOY_SETUP.md (model pool architecture §3.6)
---

# model-explorer

How a Domovoy discovers, downloads, and tests GGUF language models for local
llama.cpp inference. Companion to `DOMOVOY_SETUP.md` §3.6 (model pool
architecture) — this skill operationalizes the concepts into actionable steps.

## The Domovoy model pool concept

A Domovoy uses a pool of models organized by role:

| Role | Size range | What it does |
|------|-----------|-------------|
| **Fast** | 3–9B | Quick commands, log parsing, data gathering |
| **Daily** | 9–14B | Primary sysadmin work — configs, shell, package management |
| **Think** | 14–32B | Complex reasoning, debugging, plan-mode analysis |
| **Coder** | 14–32B | Multi-file refactors, heavy code generation |

llama-server's **router mode** (`--models-dir`) auto-discovers GGUF files,
serves them on one port, and auto-loads/unloads models on first request.
One model at a time in VRAM (or two for the always-on Fast+Daily pair).

### VRAM budget

Calculate usable VRAM: GPU VRAM minus display/compositor overhead (~1-2 GB for a
desktop GUI, negligible for headless). Q4_K_M quantization approximates params ×
0.7 GB. The always-on pair (Fast + Daily) must fit in usable VRAM simultaneously.

```
Example: 16 GB Arc GPU → ~14 GB usable
  Fast (5 GB) + Daily (8 GB) = 13 GB → fits ✅
  Think (10 GB) → auto-unloads Daily, loads alone
  Coder (15 GB) → auto-unloads everything, loads alone
```

---

## 1. Discover models

### Browse Hugging Face collections

The `GGUF-Models` org has vendor/role-based collections:
```
https://huggingface.co/collections/GGUF-Models/<vendor>
```
Good starting vendors: `Qwen`, `Gemma`, `Granite`, `DeepSeek`, `Yandex`.

### Evaluate community adoption

When comparing similar models (e.g. two uncensored Gemma-4-E4B variants), check:
- **Likes** (higher = more community trust)
- **Downloads** (higher = more real-world usage)
- **Recency** (updated in the last 3 months)
- **Creator reputation** (official orgs like `Qwen`, `HauhauCS`, `bartowski`,
  `unsloth` vs one-off uploads)

### Find GGUF files for a model

Not every model has a GGUF quant. Use the HF API to check:
```bash
curl -sH "Authorization: Bearer $HF_TOKEN" \
  "https://huggingface.co/api/models/<user>/<repo>" \
  | python3 -c "import sys,json; d=json.load(sys.stdin)
  [print(s['rfilename']) for s in d.get('siblings',[]) if '.gguf' in s['rfilename']]"
```
This lists all `.gguf` files in the repo with exact filenames.

### Where GGUF quants live

| Quantizer | Pattern | Notes |
|-----------|---------|-------|
| **bartowski** | `bartowski/<Model>-GGUF` | Most prolific quantizer. Large file variety. |
| **unsloth** | `unsloth/<Model>-GGUF` | Dynamic GGUF quantizer. |
| **QuantFactory** | `QuantFactory/<Model>-GGUF` | Community quantizer. |
| **Self-published** | Same repo as the model | Creators like `HauhauCS` and `Qwen` publish their own Q4_K_M GGUF directly. |

---

## 2. Understand quantizations

Common llama.cpp GGUF quants (Q = standard, IQ = with importance matrix, K = mixed precision):

| Quant | Size (relative to BF16) | Quality | Best for |
|-------|------------------------|---------|----------|
| Q4_K_M | ~30% | Good | **Default choice.** Balance of size/quality for most roles. |
| IQ4_XS | ~27% | Slightly better | Bigger models where every GB counts (e.g. 27B). |
| IQ4_NL | ~25% | Slightly below Q4_K_M | Same as IQ4_XS — slightly smaller variant. |
| Q5_K_M | ~36% | Better | When you can afford extra GB. |
| Q8_0 | ~50% | Excellent | Quality-critical tasks (avoid for VRAM-constrained pools). |

For the Domovoy pool: **Q4_K_M is the default.** For 27B+ models use IQ4_XS or IQ4_NL.

---

## 3. Download models

**Delegate to the `hf-model-download` skill.** It is the single source of truth
for download mechanics: finding the exact filename via HF API, setting the token,
curl download + resume, and troubleshooting. Load it with the `skill` tool when
the user is ready to download a known model.

Brief summary (repeated here only for context — `hf-model-download` is
authoritative):

- Get the exact filename from the HF API — **do not guess from the model name.**
- Set `HF_TOKEN` ephemerally, never logged.
- `curl -fL -H "Authorization: Bearer $HF_TOKEN" -o ~/models/<file>.gguf <url>`
- Restart llama-server: `systemctl --user restart llama-server.service`

---

## 4. Filename verification (critical gotcha)

**Do not assume the filename from the model name.** Casing matters:

| Repo | Expected (wrong) | Actual (correct) |
|------|------------------|-----------------|
| `deepreinforce-ai/Ornith-1.0-9B-GGUF` | `Ornith-1.0-9B-Q4_K_M.gguf` | `ornith-1.0-9b-Q4_K_M.gguf` (lowercase) |
| `Qwen/Qwen3-14B-GGUF` | `qwen3-14b-Q4_K_M.gguf` | `Qwen3-14B-Q4_K_M.gguf` (CamelCase) |

Always check the actual repo file listing (HF API) before constructing the
download URL. A 404 on a gated model may also mean the file exists but the
user hasn't accepted the model's terms — accept them on the HF website first.

---

## 5. Add models to the pool

1. Drop the `.gguf` file into `~/models/` (where `--models-dir` points).
2. Restart llama-server:
   ```bash
   systemctl --user restart llama-server.service
   ```
3. Verify via the API:
   ```bash
   curl -s http://localhost:8080/v1/models | python3 -c "
   import sys,json
   d=json.load(sys.stdin)
   [print(m['id']) for m in d['data']]
   "
   ```
   All discovered models appear in the list. No manual registration needed.

---

## 6. Test models against real Domovoy tasks

For each candidate model in a role, run representative tasks and compare:

**Fast candidates:**
- Parse a log file: "Extract all ERROR lines from this journalctl output, one per line"
- Fetch a URL: "Get the latest release version from https://api.github.com/repos/ggml-org/llama.cpp/releases/latest and return just the tag_name"
- Structured data: "List all packages owned by user=root from this pacman -Q output"

**Daily candidates:**
- Shell scripting: "Write a bash script that checks disk usage on all btrfs subvolumes and alerts if any are above 90%"
- Config analysis: "Review this nftables.conf for security issues"
- Summarization: "Read these 50 lines of journalctl output and summarize the system health"

**Think candidates:**
- Root cause analysis: "This service keeps restarting. Here are the logs. What's going on?"
- Multi-step reasoning: "We need to migrate from ext4 to btrfs on a running system. What are the steps, risks, and rollback plan?"

**Coder candidates:**
- Multi-file refactor: "Rewrite this 200-line shell script to Python with proper error handling"
- System configuration: "Generate a systemd unit file for a Go application with health checks and resource limits"

### Evaluation criteria

| Criteria | How to assess |
|----------|---------------|
| **Speed** | Time to first token + total generation time. Fast tasks need <1s TTFT. |
| **Correctness** | Does the output do what was asked? Shell commands should run without errors. |
| **VRAM fit** | Does it load alongside the always-on pair without OOM? Check `GET /v1/models` status field. |
| **Refusal rate** | For uncensored models: does it refuse reasonable sysadmin tasks (package installs, config edits)? |

## 7. Rotate models

When testing is complete, document the final pool in `DOMOVOY_SETUP.md` §3.6:

| Role | Primary | Alternate |
|------|---------|-----------|
| Fast | granite-4.1-8b Q4_K_M | ornith-1.0-9b Q4_K_M |
| Daily | gemma-4-12b-it Q4_K_M | Qwen2.5-14B-Instruct Q4_K_M |
| Think | deepseek-r1-distill-qwen-14b Q4_K_M | Qwen3-14B Q4_K_M |
| Coder | qwen3.6-27b IQ4_XS | Qwen3.6-27b IQ4_NL |

The router mode handles the rest — send requests with `"model": "<filename>"` to
route to the right one. opencode's agent-specific model config maps these to
Build/Plan/Explore agents.

---

## 8. Uncensored models — a special category

Community-fine-tuned models ("abliterated", "heretic") remove safety/refusal
training from base models. Popular creators: **HauhauCS** (26 models, highest
community adoption), `zaakirio`, `llmfan46`.

When exploring uncensored models:
- Compare **Aggressive** vs **Balanced** variants (aggressive = more refusals removed).
- Same VRAM rules apply (Q4_K_M ≈ params × 0.7 GB).
- Test refusal rate on benign sysadmin tasks — some aggressive ablations may
  still refuse harmless commands if the ablation was overdone.

Base directory: file:///home/domovoy/.agents/skills/model-explorer
