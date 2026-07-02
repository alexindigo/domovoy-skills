#!/usr/bin/env python3
"""Extract Firefox / LibreWolf bookmarks into the shared url-groups format.

Leaf skill: firefox-bookmarks-extraction (parent: browser-bookmarks-source).
Conforms to browser-bookmarks-source/FORMAT.md (bookmarks profile,
state="inactive", grouped by folder with full hierarchy preserved).

Read-only on the live profile: places.sqlite is copied to a temp file before
opening, so a running browser (or a locked DB) is never touched or blocked.

Python 3 stdlib only (sqlite3 + json) -> portable on Arch/Debian/macOS, no deps.

Usage:
  extract.py --profile <profile_dir> --out <bookmarks.json> \
             --host <host> --os <linux|darwin> \
             [--browser firefox|librewolf] [--profile-name <name>]

Empty folders are dropped (only folders that contain links are emitted).
Non-http(s) URLs (place:, javascript:, about:, etc.) are dropped.
"""
import argparse
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone


def read_browser_version(profile_dir):
    """Best-effort Firefox/LibreWolf version from compatibility.ini."""
    ini = os.path.join(profile_dir, "compatibility.ini")
    try:
        with open(ini, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("LastVersion="):
                    # e.g. LastVersion=126.0_20240501...
                    return line.split("=", 1)[1].strip().split("_", 1)[0]
    except OSError:
        pass
    return ""


def extract(places_path):
    """Return list of folder-groups from a places.sqlite copy.

    Walks moz_bookmarks (type 2 = folder, type 1 = bookmark) building each
    bookmark's ancestor folder chain into container.path. Roots are renamed to
    friendly labels.
    """
    ROOT_LABELS = {
        "menu": "Bookmarks Menu",
        "toolbar": "Bookmarks Toolbar",
        "unfiled": "Other Bookmarks",
        "mobile": "Mobile Bookmarks",
    }
    con = sqlite3.connect(places_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # id -> (parent, type, title, guid)
    nodes = {}
    for r in cur.execute(
        "SELECT id, parent, type, title, guid FROM moz_bookmarks"
    ):
        nodes[r["id"]] = dict(
            parent=r["parent"], type=r["type"], title=r["title"], guid=r["guid"]
        )

    def folder_path(node_id):
        """Build the ancestor folder title chain for a bookmark's parent."""
        path = []
        seen = set()
        cur_id = node_id
        while cur_id in nodes and cur_id not in seen:
            seen.add(cur_id)
            n = nodes[cur_id]
            if n["type"] == 2 and n["parent"] is not None:  # a folder with a parent
                label = n["title"]
                if not label and n["guid"]:
                    # root folders have well-known guid prefixes
                    for key, friendly in ROOT_LABELS.items():
                        if (n["guid"] or "").startswith(key):
                            label = friendly
                            break
                if label:
                    path.append(label)
            cur_id = n["parent"]
        path.reverse()
        return path

    # group bookmarks by their folder path
    groups = {}  # tuple(path) -> list[links]
    for r in cur.execute(
        "SELECT b.parent AS parent, b.title AS title, p.url AS url, b.dateAdded AS dateAdded "
        "FROM moz_bookmarks b JOIN moz_places p ON b.fk = p.id "
        "WHERE b.type = 1"
    ):
        url = r["url"] or ""
        if not (url.startswith("http://") or url.startswith("https://")):
            continue
        path = tuple(folder_path(r["parent"]))
        added = ""
        if r["dateAdded"]:
            try:
                # Firefox stores microseconds since epoch
                added = datetime.fromtimestamp(
                    r["dateAdded"] / 1_000_000, tz=timezone.utc
                ).isoformat()
            except (ValueError, OverflowError, OSError):
                added = ""
        groups.setdefault(path, []).append(
            {"url": url, "title": r["title"] or url, "added": added}
        )

    con.close()

    out = []
    for i, (path, links) in enumerate(sorted(groups.items())):
        if not links:  # drop empty folders
            continue
        out.append(
            {
                "id": "f%d" % i,
                "state": "inactive",
                "container": {
                    "type": "folder",
                    "path": list(path),
                    "title_hint": path[-1] if path else "(root)",
                },
                "links": links,
            }
        )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--host", required=True)
    ap.add_argument("--os", required=True, choices=["linux", "darwin"])
    ap.add_argument("--browser", default="firefox", choices=["firefox", "librewolf"])
    ap.add_argument("--profile-name", default="")
    args = ap.parse_args()

    places = os.path.join(args.profile, "places.sqlite")
    if not os.path.isfile(places):
        sys.stderr.write("no places.sqlite in %s\n" % args.profile)
        return 1

    tmpdir = tempfile.mkdtemp(prefix="ffbm-")
    try:
        tmp_places = os.path.join(tmpdir, "places.sqlite")
        shutil.copy2(places, tmp_places)
        groups = extract(tmp_places)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

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
        "groups": groups,
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    sys.stderr.write(
        "wrote %s (%d folders, %d links)\n"
        % (args.out, len(groups), sum(len(g["links"]) for g in groups))
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
