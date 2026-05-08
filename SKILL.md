---
name: uap-release-analyzer
description: Inventory, extract, and analyze tranches of declassified UAP/UFO files — including war.gov/UFO/ "PURSUE" releases, FBI Vault, NARA boxes, and AARO publications. Use this skill whenever the user points at a folder of UAP/UFO/declassified PDFs, asks "what's in this release?", references war.gov/UFO/, AARO, PURSUE, FOIA tranches, FBI 62-HQ-83894, or asks for keyword/entity/redaction analysis across a corpus of declassified documents — even if they don't explicitly ask for an "analysis." Also triggers on requests to compare tranches, summarize a single declassified PDF, classify documents by agency, or surface (b)(1)/(b)(6)/NOFORN redaction patterns. Produces a standardized inventory.csv, per-file digest, entities.json, and REPORT.md.
license: Complete terms in LICENSE.txt
---

# UAP / Declassified Release Analyzer

This skill turns a folder of declassified UAP/UFO documents into a structured analytic report. It was built from a real workflow against the May 2026 war.gov/UFO/ "PURSUE" tranche (162 files, 4,000+ pages, mixed FBI/DOW/NASA/DOS/NARA sources), so it's tuned to the quirks of that universe — but it generalizes to any tranche of FOIA-released government PDFs.

## When to use

Trigger on prompts like "analyze the UFO files I just downloaded", "build me a report on this UAP release", "what's in `~/Downloads/release_01/`?", "compare release 1 and release 2", "find redaction patterns in these FBI files", "summarize this AARO PDF", or whenever the user references a directory of declassified documents and wants any kind of summary, inventory, or pattern surfacing. Also trigger if the user just dumps a path and asks "what's interesting in here?" — this skill is the right tool.

## Why a skill

The work has a fixed shape that repeats across every new tranche:

1. Inventory — what files came down, sizes, page counts, which agency.
2. Text extraction — pull text where there is a text layer; flag the (often majority) of files that are scanned and need OCR.
3. Entity surfacing — locations, agencies, phenomena vocabulary, named people.
4. Redaction pattern analysis — which FOIA exemptions show up where, which files are most redacted.
5. Cross-document patterns — year clusters, agency × location heatmap, names that appear in 5+ files.
6. A standardized report the user can read in ten minutes.

Doing this freshly every time wastes effort and produces inconsistent outputs. The bundled scripts make every tranche analyzable the same way.

## The standard workflow

Run scripts in this order. Each writes intermediate artifacts that the next step consumes. They are **idempotent and incremental** — re-running on the same folder skips work that's already done.

```
release_root/
  release_NN/                 # the actual PDFs/PNGs/JPGs (input)
  text/                       # extracted text per PDF (created)
  inventory.csv               # one row per file (created)
  analytics/                  # aggregated outputs (created)
    top_terms.csv
    terms_by_agency.csv
    entities.json
    per_file_digest.csv
    cross_doc.json
  REPORT.md                   # human-readable analytic writeup (created)
```

**Step 1 — Inventory.** Run `scripts/inventory.py <release_root>`. This walks the release directory, classifies each file by filename prefix (see `references/agency_vocab.md`), reads PDF page counts, and writes `inventory.csv`. Don't write inventory by hand — the script handles encrypted PDFs, weird filenames with spaces or em-dashes, and files that pypdf can't open.

**Step 2 — Text extraction.** Run `scripts/extract_text.py <release_root> [start] [end]`. Extracts text via pdfplumber, writing one `.txt` per PDF into `text/`. Skips files that already have a non-empty `.txt`. Many FBI / NARA / older photo-PDFs have **no text layer** — those will produce 0-char files; that's expected and fine, the analytics treat them as "scanned, OCR needed". The optional `[start] [end]` slice arguments let you process in chunks if your sandbox has a per-call timeout (the war.gov FBI sections are 200+ pages each — extract them in batches of ~25 if running in a 45-second-call environment).

**Run scripts in the foreground of your turn**, not via background-and-end-turn patterns. The pipeline is fast enough (a few minutes from cold) that you can stay in-turn. If a single `extract_text.py` call would actually time out, prefer the `[start] [end]` chunking pattern over backgrounding — chunked calls each finish quickly, the script is idempotent, and progress is visible.

**Step 3 — Analytics.** Run `scripts/analyze.py <release_root>`. Reads the extracted text + inventory, then writes the contents of `analytics/`. This is fast even on 800K+ characters of text.

**Step 4 — Report.** Run `scripts/build_report.py <release_root>`. Reads inventory + analytics and writes a `REPORT.md` with the sections listed under "Report structure" below.

When the user just says "analyze the release at `<path>`", run all four in sequence with that path. When they ask a narrower question ("how many files?", "which file is most redacted?"), call only the relevant script or read the existing artifacts directly.

## Report structure

Always use this exact section order in `REPORT.md` so reports across tranches stay comparable. If a section has no data for this tranche, leave a one-line "no data" note — don't omit the heading.

```
# <Release name> — Raw Analytics
**Source:** ... · **Cleared for release:** ...
**Files in this analysis:** N of M (note any gaps)

## 1. Inventory                    — counts, total size, page counts, by agency
## 2. What's actually in the release  — narrative summary of the major buckets
## 3. Where the activity is concentrated  — top locations
## 4. Phenomena terminology         — UAP/craft/orb/disc/etc. with counts
## 5. Agency cross-references       — agencies named in text
## 6. Year clusters                 — when is this material from
## 7. Redactions                    — top markers + most-redacted files
## 8. Notable individual files
## 9. Cross-document patterns
## 10. What's missing / caveats     — OCR gaps, files we couldn't pull, etc.
## 11. Files in this analysis       — paths to inventory.csv / analytics/*
```

The "What's missing" section matters — it's what makes the report honest. Always call out files we couldn't OCR, files referenced on a source page but not downloaded, and heuristic limits of the entity extraction.

## Agency classification

Files are classified by filename prefix. The full vocabulary is in `references/agency_vocab.md`. The high-confidence prefixes from the war.gov universe:

- `65_hs1*`, `fbi-photo-*`, `usper-*`, `serial*`, `2024-04-30-*` → FBI
- `dow-uap*`, `western_us_event*` → DOW (Department of War)
- `nasa-uap*` → NASA
- `dos-uap*`, `059uap*` → DOS (State)
- `18_*`, `38_*`, `59_*`, `255*`, `331_*`, `341_*`, `342_*` → NARA (record-group prefixes)
- otherwise → OTHER (flag for the user; might be a new bucket worth adding to the vocab)

If you encounter a tranche with prefixes not in the vocab, add them to `references/agency_vocab.md` (the table) and `scripts/inventory.py` + `scripts/analyze.py` (`PREFIX_RULES`) rather than scattering inline filename checks across scripts. A useful threshold: if `OTHER` exceeds ~3% of files in any tranche, that's a signal the vocab needs extending, not the data being weird.

When bootstrapping a brand-new tranche (e.g., the user has just downloaded `release_02/` and asks "what's the fastest way to a written report?"), surface this vocab-extension workflow in your reply alongside `run_all.py`. Otherwise the user will discover the OTHER bucket only after the fact.

## FOIA / classification markers

`references/foia_codes.md` lists the FOIA exemptions and classification stamps to look for. Most of the meaningful redaction signal in modern tranches comes from `(b)(1)` (national security), `(b)(3)` (statutory), `(b)(6)` (personal privacy), and the classification banners `SECRET//NOFORN`, `REL TO USA`, `CUI`, `FOUO`. The analyzer counts these by file so the report can name the most-redacted documents.

## Pulling files from war.gov/UFO/ (PURSUE releases)

If the user wants to pull from the source page rather than analyzing files they already have, see `references/war_gov_quirks.md`. It documents the things that bit us on the first run: the page renders 10 records per page across paginated DOM, the "Download" button is hooked through `<a download>`-style behavior so URLs are only available after the modal opens, ~28 of 162 records are served via inline viewer (no clean URL), and `www.war.gov` is typically not on a workspace egress allowlist (you'll need browser-driven downloads or a one-time allowlist). Don't reinvent the scrape — check the reference first.

## Working with the user

- **Start narrow.** Ask for the path if they didn't give one. Don't guess.
- **Show progress.** Tranches are big (the May 2026 release was 2.5 GB / 4,000 pages); print `[N/total]` lines as you go so the user isn't flying blind.
- **Don't run OCR by default.** Tesseract on 4,000 scanned pages takes hours. Note the gap in the "What's missing" section and offer OCR as a follow-up.
- **Surface cross-tranche links** if the user has more than one release in the parent folder — a sibling `release_02/` makes "what's new vs. release_01?" the obvious next question.
- **Honest caveats.** Entity extraction here is keyword-list + regex, not full NER. Year mentions ≠ incident dates. Say so in the report.

## Bundled scripts

- `scripts/inventory.py <release_root>` — build inventory.csv
- `scripts/extract_text.py <release_root> [start] [end]` — extract text in optional chunks
- `scripts/analyze.py <release_root>` — write analytics/
- `scripts/build_report.py <release_root>` — write REPORT.md
- `scripts/run_all.py <release_root>` — convenience: run the four in order

## Bundled references

- `references/agency_vocab.md` — filename-prefix → agency rules
- `references/foia_codes.md` — FOIA exemptions and classification stamps
- `references/war_gov_quirks.md` — how war.gov/UFO/ is structured + scraping notes

Read references on demand. Don't preload them into context unless the user's question is in their domain.
