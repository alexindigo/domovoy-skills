#!/usr/bin/env python3
"""Extract Chromium-family bookmarks into the shared url-groups format.

Leaf skill: chromium-bookmarks-extraction (parent: browser-bookmarks-source).
Covers Chrome, Chromium, Brave, Edge, Vivaldi (shared "Bookmarks" JSON format).
Conforms to browser-bookmarks-source/FORMAT.md (bookmarks profile,
state="inactive", grouped by folder with full hierarchy preserved).

The "Bookmarks" file is plain JSON (no SQLite). Copied to a temp file before
reading so a running browser is never disturbed.

Python 3 stdlib only (json) -> portable on Arch/Debian/macOS, no deps.

Usage:
  extract.py --profile <profile_dir> --out <bookmarks.json> \
             --host <host> --os <linux|darwin> \
             --browser <chrome|chromium|brave|edge|vivaldi> \
             [--profile-name <name>]

Empty folders are dropped. Non-http(s) URLs are dropped.
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone

ROOT_LABELS = {
    "bookmark_bar": "Bookmark Bar",
    "other": "Other Bookmarks",
    "synced": "Mobile Bookmarks",
}


def chrome_time_to_iso(microseconds_str):
    """Chromium timestamps: microseconds since 1601-01-01 UTC."""
    try:
        us = int(microseconds_str)
    except (TypeError, ValueError):
        return ""
    if us <= 0:
        return ""
    # 11644473600 seconds between 1601-01-01 and 1970-01-01
    try:
        epoch = us / 1_000_000 - 11644473600
        return (
            datetime.fromtimestamp(epoch, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
    except (ValueError, OverflowError, OSError):
        return ""


def walk(node, path, groups):
    """Recurse a bookmark tree node, accumulating links grouped by folder path."""
    ntype = node.get("type")
    if ntype == "folder":
        name = node.get("name", "")
        new_path = path + ([name] if name else [])
        for child in node.get("children", []):
            walk(child, new_path, groups)
    elif ntype == "url":
        url = node.get("url", "")
        if not (url.startswith("http://") or url.startswith("https://")):
            return
        key = tuple(path)
        groups.setdefault(key, []).append(
            {
                "url": url,
                "title": node.get("name") or url,
                "added": chrome_time_to_iso(node.get("date_added")),
            }
        )


def read_browser_version(profile_dir):
    """Best-effort version from the profile's 'Last Version' file (User Data root)."""
    # 'Last Version' lives in the User Data dir (parent of the profile dir).
    for cand in (
        os.path.join(profile_dir, "Last Version"),
        os.path.join(os.path.dirname(profile_dir.rstrip("/")), "Last Version"),
    ):
        try:
            with open(cand, "r", encoding="utf-8", errors="replace") as f:
                return f.read().strip()
        except OSError:
            continue
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--host", required=True)
    ap.add_argument("--os", required=True, choices=["linux", "darwin"])
    ap.add_argument(
        "--browser",
        required=True,
        choices=["chrome", "chromium", "brave", "edge", "vivaldi"],
    )
    ap.add_argument("--profile-name", default="")
    args = ap.parse_args()

    bm = os.path.join(args.profile, "Bookmarks")
    if not os.path.isfile(bm):
        sys.stderr.write("no Bookmarks file in %s\n" % args.profile)
        return 1

    tmpdir = tempfile.mkdtemp(prefix="crbm-")
    try:
        tmp_bm = os.path.join(tmpdir, "Bookmarks")
        shutil.copy2(bm, tmp_bm)
        with open(tmp_bm, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        sys.stderr.write("failed to read Bookmarks: %s\n" % e)
        return 1
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    groups = {}
    roots = data.get("roots", {})
    for root_key, friendly in ROOT_LABELS.items():
        node = roots.get(root_key)
        if isinstance(node, dict):
            # Seed the path with the friendly root label and recurse the root's
            # CHILDREN directly, so the root node's own name isn't pushed twice.
            for child in node.get("children", []):
                walk(child, [friendly], groups)

    out = []
    for i, (path, links) in enumerate(sorted(groups.items())):
        if not links:  # drop empty folders
            continue
        out.append(
            {
                "id": "c%d" % i,
                "state": "inactive",
                "container": {
                    "type": "folder",
                    "path": list(path),
                    "title_hint": path[-1] if path else "(root)",
                },
                "links": links,
            }
        )

    doc = {
        "format": "url-groups",
        "version": "1",
        "datatype": "bookmarks",
        "origin": {
            "host": args.host,
            "os": args.os,
            "browser": args.browser,
            "browser_version": read_browser_version(args.profile),
            "profile": args.profile_name or os.path.basename(args.profile.rstrip("/")),
        },
        "generated": datetime.now().astimezone().isoformat(),
        "groups": out,
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    sys.stderr.write(
        "wrote %s (%d folders, %d links)\n"
        % (args.out, len(out), sum(len(g["links"]) for g in out))
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
