#!/usr/bin/env python3
"""inventory.py <release_root>

Build inventory.csv with one row per file in <release_root>/release_*/.
Captures filename, agency (from prefix), document type, size, and PDF page
count. Idempotent — overwrites inventory.csv each run.
"""
import csv, os, re, sys, warnings
from pathlib import Path

warnings.filterwarnings("ignore")

# --- agency classification ----------------------------------------------------
PREFIX_RULES = [
    (("65_hs1", "fbi-photo", "usper-", "serial", "2024-04-30-"), "FBI"),
    (("dow-uap", "western_us_event"), "DOW"),
    (("nasa-uap",), "NASA"),
    (("dos-uap", "059uap"), "DOS"),
    (("18_", "38_", "59_", "255_", "255-T-", "331_", "341_", "342_"), "NARA"),
]

def classify(name: str) -> str:
    n = name.lower()
    for prefixes, agency in PREFIX_RULES:
        if any(n.startswith(p) for p in prefixes):
            return agency
    return "OTHER"

def doc_type(name: str) -> str:
    n = name.lower()
    if n.startswith("fbi-photo") or n.startswith("nasa-uap-vm"):
        return "image"
    return "document"


def find_release_dirs(root: Path):
    # accept either: release_root contains release_NN/ subdirs, or release_root
    # IS a single release directory.
    children = [p for p in root.iterdir() if p.is_dir() and p.name.lower().startswith("release_")]
    if children:
        return sorted(children)
    if any(p.is_file() for p in root.iterdir()):
        return [root]
    raise SystemExit(f"No release_* subdir or files found under {root}")


def page_count(path: Path):
    if path.suffix.lower() != ".pdf":
        return ""
    try:
        import pypdf  # type: ignore
        with open(path, "rb") as f:
            r = pypdf.PdfReader(f)
            if r.is_encrypted:
                try:
                    r.decrypt("")
                except Exception:
                    pass
            return len(r.pages)
    except Exception as e:
        return f"ERR:{type(e).__name__}"


def main(release_root: str) -> int:
    root = Path(release_root).expanduser().resolve()
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        return 2

    out_path = root / "inventory.csv"
    rows = []
    for rel_dir in find_release_dirs(root):
        for p in sorted(rel_dir.iterdir()):
            if not p.is_file():
                continue
            size = p.stat().st_size
            rows.append({
                "release":  rel_dir.name,
                "filename": p.name,
                "agency":   classify(p.name),
                "doc_type": doc_type(p.name),
                "ext":      p.suffix.lower().lstrip("."),
                "size_bytes": size,
                "size_mb":  round(size / 1048576, 2),
                "pages":    page_count(p),
            })

    if not rows:
        print("No files found", file=sys.stderr)
        return 1

    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    by_agency = {}
    for r in rows:
        by_agency[r["agency"]] = by_agency.get(r["agency"], 0) + 1
    total_pages = sum(r["pages"] for r in rows if isinstance(r["pages"], int))
    print(f"Inventoried {len(rows)} files across {len(set(r['release'] for r in rows))} release(s)")
    print(f"Total bytes: {sum(r['size_bytes'] for r in rows):,}")
    print(f"Total PDF pages: {total_pages:,}")
    print(f"By agency: {by_agency}")
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: inventory.py <release_root>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
