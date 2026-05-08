#!/usr/bin/env python3
"""extract_text.py <release_root> [start] [end]

Extract text from every PDF in <release_root>/release_*/ to <release_root>/text/.
Skips PDFs that already have a non-empty .txt sibling. The optional [start end]
slice processes a subset (useful when sandboxes have a per-call timeout — the
big FBI sections take a while).

A 0-character output is reported but kept — it signals "scanned, OCR needed"
to the analyzer and report. Don't auto-OCR; that's a multi-hour job and the
user should choose to do it.
"""
import signal, sys, warnings
from pathlib import Path

warnings.filterwarnings("ignore")


def find_release_dirs(root: Path):
    children = [p for p in root.iterdir() if p.is_dir() and p.name.lower().startswith("release_")]
    if children:
        return sorted(children)
    return [root]


class _Timeout(Exception):
    pass


def _alarm_handler(*_):
    raise _Timeout()


def main(args):
    if not args:
        print("usage: extract_text.py <release_root> [start] [end]", file=sys.stderr)
        return 2
    import pdfplumber  # type: ignore

    root = Path(args[0]).expanduser().resolve()
    start = int(args[1]) if len(args) > 1 else 0
    end   = int(args[2]) if len(args) > 2 else 10**9

    out_dir = root / "text"
    out_dir.mkdir(exist_ok=True)

    pdfs = []
    for rel in find_release_dirs(root):
        pdfs.extend(sorted(p for p in rel.iterdir() if p.suffix.lower() == ".pdf"))

    batch = pdfs[start:end]
    signal.signal(signal.SIGALRM, _alarm_handler)

    cached = 0
    extracted = 0
    empty = 0
    errored = []

    for i, p in enumerate(batch, start + 1):
        out = out_dir / (p.stem + ".txt")
        if out.exists() and out.stat().st_size > 0:
            cached += 1
            if i % 10 == 0 or i == len(batch) + start:
                print(f"[{i}] cached  {p.name[:70]}", flush=True)
            continue
        size_mb = p.stat().st_size / 1048576
        try:
            signal.alarm(min(180, max(30, int(size_mb * 4))))
            chars = 0
            with pdfplumber.open(p) as pdf, open(out, "w") as f:
                for page in pdf.pages:
                    try:
                        t = page.extract_text() or ""
                    except Exception:
                        t = ""
                    f.write(t + "\n\n")
                    chars += len(t)
            signal.alarm(0)
            if chars == 0:
                empty += 1
                tag = "empty"
            else:
                tag = f"chars={chars}"
            extracted += 1
            print(f"[{i}] ok {tag}  {p.name[:70]}", flush=True)
        except _Timeout:
            signal.alarm(0)
            print(f"[{i}] TIMEOUT  {p.name[:70]}", flush=True)
            errored.append((p.name, "timeout"))
            if out.exists() and out.stat().st_size == 0:
                out.unlink()
        except Exception as e:
            signal.alarm(0)
            print(f"[{i}] ERR {type(e).__name__}: {e}  {p.name[:70]}", flush=True)
            errored.append((p.name, type(e).__name__))
            if out.exists() and out.stat().st_size == 0:
                out.unlink()

    print("=" * 60)
    print(f"Extracted: {extracted}  Cached: {cached}  Empty (likely scanned): {empty}  Errors: {len(errored)}")
    if errored:
        for n, e in errored[:10]:
            print(f"  ERR {e}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
