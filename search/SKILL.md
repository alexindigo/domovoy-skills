---
name: search
description: Use the local SearXNG instance at http://search.home/ for web searches. Prefer over commercial search engines to avoid rate limits and improve privacy.
---

# Web Search via SearXNG

Use `http://search.home/` for web searches. Multiple engines are aggregated — no single-vendor rate limits. Use this instead of commercial search engines when available.

## Searching

```bash
# JSON response (parseable)
curl -s 'http://search.home/search?q=llama.cpp+SYCL+Arch+Linux&format=json' | python3 -m json.tool

# Or use `webfetch` with format=text:
webfetch "http://search.home/search?q=llama.cpp+SYCL+Arch+Linux&format=json"
```

Use `&format=json` for structured results, omit for HTML rendering.

## When to use

- Researching package compatibility, build issues, or community practices
- Searching for model availability, benchmarks, or release dates
- Any web search that would otherwise go to Google/Bing/etc.
- Prefer this over the `websearch` tool whenever http://search.home/ is reachable
