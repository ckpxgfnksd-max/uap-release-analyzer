# uap-release-analyzer

A Claude Code / Claude.ai skill that turns a folder of declassified UAP/UFO documents — war.gov "PURSUE" releases, FBI Vault tranches, NARA boxes, AARO publications — into a structured analytic report.

## What it does

Run it against a release directory (e.g. `~/Documents/UFO/release_01/`) and it produces:

- `inventory.csv` — one row per file: agency (inferred from filename prefix), document type, page count, size
- `text/*.txt` — extracted text via pdfplumber, with empty files flagged for the (often majority) of files that are scanned with no text layer
- `analytics/`
  - `top_terms.csv`, `terms_by_agency.csv` — token frequencies
  - `entities.json` — locations, agencies, phenomena vocabulary, year clusters, names appearing in 5+ files
  - `per_file_digest.csv` — top terms / locations / redactions / 2-sentence summary per file
  - `cross_doc.json` — redaction patterns, agency totals, scanned-vs-text split
- `REPORT.md` — 11-section human-readable analytic writeup

The four scripts are idempotent and incremental — re-running on the same folder skips work that's already done.

## Installation

```bash
# Inside Claude Code (per-user skills directory)
git clone https://github.com/ckpxgfnksd-max/uap-release-analyzer.git \
  ~/.claude/skills/uap-release-analyzer
```

Or package via `skill-creator`:

```bash
python -m scripts.package_skill /path/to/uap-release-analyzer
# produces uap-release-analyzer.skill — install via Claude Code UI
```

Dependencies: `pdfplumber`, `pypdf`. Install via `pip install pdfplumber pypdf`.

## Layout

```
uap-release-analyzer/
├── SKILL.md              # frontmatter + workflow
├── scripts/
│   ├── inventory.py
│   ├── extract_text.py
│   ├── analyze.py
│   ├── build_report.py
│   └── run_all.py        # convenience: run the four in order
├── references/
│   ├── agency_vocab.md   # filename-prefix → agency rules
│   ├── foia_codes.md     # FOIA exemptions and classification stamps
│   └── war_gov_quirks.md # how war.gov/UFO/ is structured + scraping notes
├── evals/evals.json      # 4 test cases used to iterate the skill
├── ARTICLE.md            # development notes (English)
├── ARTICLE_CN.md         # 中文版开发笔记
└── LICENSE.txt
```

## Usage

```bash
# One-shot: full pipeline
python scripts/run_all.py ~/Documents/UFO/release_01/

# Or step-by-step (inventory and extract are the slow parts; both are idempotent)
python scripts/inventory.py    ~/Documents/UFO/release_01/
python scripts/extract_text.py ~/Documents/UFO/release_01/        # all files
python scripts/extract_text.py ~/Documents/UFO/release_01/ 0 25   # chunked
python scripts/analyze.py      ~/Documents/UFO/release_01/
python scripts/build_report.py ~/Documents/UFO/release_01/
```

## Example dataset

The May 2026 war.gov "PURSUE" release this skill was tuned against is mirrored at [`ckpxgfnksd-max/uap-release-01`](https://github.com/ckpxgfnksd-max/uap-release-01) (Git LFS, **~3.7 GB / 160 files**: 118 PDFs, 28 MP4 videos, 14 images). Clone it as your `release_01/` to reproduce the eval scoreboard:

```bash
git lfs install   # one-time
git clone https://github.com/ckpxgfnksd-max/uap-release-01.git ~/Documents/UFO/release_01
python scripts/run_all.py ~/Documents/UFO/release_01
```

Or fetch only the buckets you care about:

```bash
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/ckpxgfnksd-max/uap-release-01.git ~/Documents/UFO/release_01
cd ~/Documents/UFO/release_01

git lfs pull --include "dow-uap-*.pdf"     # text-bearing DOW mission report PDFs
git lfs pull --include "dow-uap-pr*.mp4"   # 27 DOW Unresolved-Report videos (1.3 GB)
git lfs pull --include "65_hs1*"           # heavy FBI scanned sections
```

The 28 videos in the corpus aren't analyzed by this skill — `analyze.py` only reads PDF text. They're mirrored for completeness so future video-aware analysis (e.g., scene-classification or transcript extraction) has a stable input set. The skill flags any non-PDF file as `(image file — vision analysis required)` or similar in `per_file_digest.csv` and skips it for text analytics.

## Eval scoreboard (iteration-1)

| Eval | with skill | baseline | Δ |
|---|---|---|---|
| Full-tranche walkthrough | 100% | 60% | +40 |
| Single-file summary | 100% | 100% | 0 |
| Scanned-tranche honest caveats | 100% | 88% | +12 |
| Fresh-tranche bootstrap | 88% | 50% | +38 |
| **Mean** | **97%** | **74%** | **+23** |

See `ARTICLE.md` for the build story and the bugs the eval surfaced.

## Honest caveats

- Entity extraction is keyword-list + regex, not full NER. Year mentions ≠ incident dates.
- Scanned PDFs (no text layer) produce 0-char `.txt` files by design — the analyzer treats them as "OCR needed" rather than running OCR (multi-hour). Run Tesseract as a follow-up if you need that content searchable.
- The agency vocabulary is tuned to the May 2026 war.gov tranche. New tranches with new prefixes should be added to `references/agency_vocab.md` and `scripts/inventory.py PREFIX_RULES`.

## License

MIT. See `LICENSE.txt`.
