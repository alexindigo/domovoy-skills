---
name: search
description: Use the local SearXNG instance for web searches. Prefer over commercial search engines to avoid rate limits and improve privacy. Reads the instance URL from setup/<hostname>/ENVIRONMENT.md.
---

# Web Search via SearXNG

Use the **household SearXNG instance** for web searches. Multiple engines are
aggregated — no single-vendor rate limits. Prefer this over commercial search
engines when available.

## Instance URL

The SearXNG URL is configured per machine in `setup/<hostname>/ENVIRONMENT.md`
under `Services → SearXNG`. Read that value and substitute it for `$SEARXNG_URL`
in the commands below.

Typical value: `http://search.home/` (depends on the household's DNS and
network layout — check ENVIRONMENT.md, don't assume).

## Searching

```bash
# JSON response (parseable)
curl -s "$SEARXNG_URL/search?q=llama.cpp+SYCL+Arch+Linux&format=json" | python3 -m json.tool

# Or use `webfetch` with format=text:
webfetch "$SEARXNG_URL/search?q=llama.cpp+SYCL+Arch+Linux&format=json"
```

Use `&format=json` for structured results, omit for HTML rendering.

## When to use

- Researching package compatibility, build issues, or community practices
- Searching for model availability, benchmarks, or release dates
- Any web search that would otherwise go to Google/Bing/etc.
- Prefer this over the `websearch` tool whenever the SearXNG instance is reachable
