---
name: hf-model-download
description: Download a GGUF model from Hugging Face using only curl (zero dependencies). User provides the HF repo and desired quant; this skill finds the exact filename, downloads it, and handles authentication, resuming, and filename-case gotchas. Use when the user knows WHICH model they want and just needs help downloading it. For discovering and evaluating new models, use model-explorer instead.
license: GPL-3.0-or-later
compatibility: opencode
metadata:
  family: infrastructure
  topic: models
  related: model-explorer
---

# hf-model-download

Download a specific GGUF model from Hugging Face using just `curl` — no pip
packages, no `huggingface-cli`. For the user who already knows which model they
want and needs a quick, dependency-free download.

For discovering new models, evaluating community adoption, or browsing
collections, use the `model-explorer` skill instead.

---

## 1. Get the exact filename (HF API)

Do NOT guess the filename from the model name. Casing varies by repo. Use the
HF API to list actual files:

```bash
curl -sH "Authorization: Bearer $HF_TOKEN" \
  "https://huggingface.co/api/models/<user>/<repo>" \
  | python3 -c "import sys,json; d=json.load(sys.stdin)
  [print(s['rfilename']) for s in d.get('siblings',[]) if '.gguf' in s['rfilename']]"
```

Pick the Q4_K_M variant (or the quant the user asked for) from the list.

## 2. Set up the token

Get one at `huggingface.co/settings/tokens`. Set it ephemerally:

```bash
export HF_TOKEN="hf_..."    # in-memory only — never log, never write to disk
```

Verify:
```bash
curl -sH "Authorization: Bearer $HF_TOKEN" https://huggingface.co/api/whoami
```

## 3. Download

```bash
curl -fL --progress-bar \
  -H "Authorization: Bearer $HF_TOKEN" \
  -o ~/models/<filename>.gguf \
  "https://huggingface.co/<user>/<repo>/resolve/main/<filename>.gguf"
```

- `-f` – fail on HTTP errors (don't save a 404 page as a .gguf).
- `-L` – follow LFS redirects.
- `resolve/main/` – CDN path for the latest commit.

## 4. Resume an interrupted download

Add `-C -` to pick up where it left off:

```bash
curl -fLC - --progress-bar -H "Authorization: Bearer $HF_TOKEN" \
  -o ~/models/<filename>.gguf \
  "https://huggingface.co/<user>/<repo>/resolve/main/<filename>.gguf"
```

## 5. Add to the pool

The file lands in `~/models/` (llama-server's `--models-dir`). Restart:

```bash
systemctl --user restart llama-server.service
```

Verify it appears:
```bash
curl -s http://localhost:8080/v1/models
```

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| HTTP 404 | Wrong filename (case mismatch) | Check step 1 — get the real filename from the API. |
| HTTP 401 | Gated model, not accepted | Visit the HF repo page and click "Agree and access repository". |
| HTTP 401 | Bad/invalid token | Re-export `HF_TOKEN` — verify with `whoami`. |
| curl hangs | Large file, slow connection | Add `--limit-rate 10M` to avoid saturating your pipe. |

## Security

**The token must never appear in logs, output, or maintenance reports.** Pass
it as `export HF_TOKEN="..."` in the same shell, run the download, then
unset it or close the shell. The `Authorization` header is the only place it's
used. Per Domovoy safety rules: secrets are never logged.

Base directory: file:///home/domovoy/.agents/skills/hf-model-download
