#!/usr/bin/env python3
"""
build_index.py — scan writeups/**/<challenge>.md and write index.json, which
hackchester.net/writeups reads.

    python3 scripts/build_index.py            # write index.json
    python3 scripts/build_index.py --check    # validate only, exit 1 on errors

Layout (see README.md):

    writeups/<YEAR>/<CTF Name>/<challenge>.md   # one writeup, YAML frontmatter
    writeups/assets/<YEAR>/<image>              # images

Standard library only.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WRITEUPS_DIR = os.path.join(ROOT, "writeups")
OUT = os.path.join(ROOT, "index.json")
EXCERPT_LEN = 180

errors, warnings = [], []
err = lambda p, m: errors.append(f"{p}: {m}")
warn = lambda p, m: warnings.append(f"{p}: {m}")


# ---------------------------------------------------------------- frontmatter

def scalar(v):
    v = v.strip()
    if len(v) >= 2 and v[0] in "\"'" and v[-1] == v[0]:
        v = v[1:-1]
    return v


def to_list(v):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        return [scalar(x) for x in re.split(r",", v[1:-1]) if x.strip()]
    return [scalar(x) for x in v.split(",") if x.strip()] if v else []


def to_bool(v):
    return scalar(v).lower() in ("true", "yes", "1")


def parse_frontmatter(text, relpath):
    """Return (meta dict, body). meta keys lowercased."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        err(relpath, "must start with a YAML frontmatter block (--- ... ---)")
        return {}, text
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        err(relpath, "frontmatter block is not closed with ---")
        return {}, text
    meta = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"\s*([A-Za-z_]+)\s*:\s*(.*)$", line)
        if m:
            meta[m.group(1).lower()] = m.group(2)
    body = "\n".join(lines[end + 1:])
    return meta, body


def excerpt_from(body):
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith(("#", "|", "```", ">", "!", "<", "-", "*", "<!--")):
            continue
        s = re.sub(r"[`*\[\]()]", "", s)
        return (s[:EXCERPT_LEN] + "…") if len(s) > EXCERPT_LEN else s
    return ""


def git_first_commit_date(relpath):
    try:
        out = subprocess.run(
            ["git", "log", "--diff-filter=A", "--follow", "--format=%cs", "--", relpath],
            cwd=ROOT, capture_output=True, text=True, timeout=10,
        ).stdout.strip().splitlines()
        return out[-1] if out else ""
    except Exception:
        return ""


# ---------------------------------------------------------------- main

def build():
    writeups = []
    if not os.path.isdir(WRITEUPS_DIR):
        return {"generated": "", "writeups": []}

    for dirpath, dirnames, filenames in os.walk(WRITEUPS_DIR):
        rel_dir = os.path.relpath(dirpath, WRITEUPS_DIR)
        if rel_dir == "assets" or rel_dir.startswith("assets" + os.sep):
            continue
        for fn in sorted(filenames):
            if not fn.endswith(".md") or fn.upper() in ("README.MD", "TEMPLATE.MD"):
                continue
            full = os.path.join(dirpath, fn)
            path = os.path.relpath(full, ROOT).replace(os.sep, "/")            # writeups/2025/CTF/x.md
            wid = os.path.relpath(full, WRITEUPS_DIR).replace(os.sep, "/")[:-3]  # 2025/CTF/x
            parts = wid.split("/")
            if len(parts) < 3:
                warn(path, "expected writeups/<year>/<ctf>/<challenge>.md — skipped")
                continue
            year, ctf = parts[0], parts[1]

            meta, body = parse_frontmatter(open(full, encoding="utf-8").read(), path)
            if not meta:
                continue

            title = scalar(meta.get("title", "")) or parts[-1].replace("-", " ").title()
            authors = to_list(meta.get("author", "")) or to_list(meta.get("authors", ""))
            if not authors:
                err(path, "author is required in the frontmatter")
            categories = to_list(meta.get("categories", "")) or to_list(meta.get("category", ""))
            category = (categories[0] if categories else "misc")
            tags = [t.lower() for t in to_list(meta.get("tags", ""))]

            date = scalar(meta.get("date", ""))
            if date and not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
                warn(path, f"date '{date}' is not YYYY-MM-DD")
                date = ""
            if not date:
                date = git_first_commit_date(path)

            if "used_ai" not in meta:
                warn(path, "no used_ai field — defaulting to false")

            writeups.append({
                "id": wid,
                "path": path,
                "title": title,
                "authors": authors,
                "date": date,
                "year": year,
                "ctf": ctf,
                "category": category,
                "categories": categories,
                "tags": tags,
                "partial_solve": to_bool(meta.get("partial_solve", "false")),
                "used_ai": to_bool(meta.get("used_ai", "false")),
                "excerpt": excerpt_from(body),
            })

    writeups.sort(key=lambda w: (w["date"] or "", w["id"]), reverse=True)
    ctfs = {}
    for w in writeups:
        ctfs.setdefault(w["ctf"], {"name": w["ctf"], "year": w["year"]})
    return {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ctfs": [{"slug": s, **v} for s, v in sorted(ctfs.items(), key=lambda kv: (kv[1]["year"], kv[0]), reverse=True)],
        "writeups": writeups,
    }


def main():
    check_only = "--check" in sys.argv
    index = build()
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error:   {e}")
    n = len(index["writeups"])
    if errors:
        print(f"\n{n} writeup(s), {len(errors)} error(s)")
        sys.exit(1)
    if check_only:
        print(f"\nok — {n} writeup(s), {len(warnings)} warning(s)")
        return
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"\nwrote index.json — {n} writeup(s), {len(warnings)} warning(s)")


if __name__ == "__main__":
    main()
