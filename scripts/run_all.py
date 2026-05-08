#!/usr/bin/env python3
"""run_all.py <release_root>

Convenience runner: inventory → extract_text → analyze → build_report.
"""
import subprocess, sys
from pathlib import Path

HERE = Path(__file__).parent

def step(name, args):
    print(f"\n=== {name} ===")
    r = subprocess.run([sys.executable, str(HERE / name)] + list(args))
    if r.returncode:
        print(f"{name} failed (rc={r.returncode})", file=sys.stderr)
        sys.exit(r.returncode)

def main(args):
    if not args:
        print("usage: run_all.py <release_root>", file=sys.stderr)
        return 2
    root = args[0]
    step("inventory.py", [root])
    step("extract_text.py", [root])
    step("analyze.py", [root])
    step("build_report.py", [root])
    print(f"\nDone. See {Path(root)/'REPORT.md'}")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
