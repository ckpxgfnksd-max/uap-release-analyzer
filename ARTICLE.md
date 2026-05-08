# Shipping a UAP-release analyzer skill: what the eval loop actually catches

I had a 2.5 GB folder of declassified UAP files from war.gov sitting on disk — 132 PDFs and images across FBI, DOW, NASA, DOS and NARA. The job was to build a Claude skill that takes any folder like this and turns it into a structured report I can read in ten minutes. Then run the skill-creator eval loop on it until the deltas plateau. Here's what fell out.

## The skill, in one paragraph

Four idempotent Python scripts: `inventory.py` (filename-prefix → agency, page counts), `extract_text.py` (pdfplumber, skips already-extracted, flags scanned files), `analyze.py` (keyword-list + regex over locations / phenomena / FOIA exemptions / redaction banners — deliberately not full NER, so it stays auditable), and `build_report.py` (an 11-section `REPORT.md`). Plus three reference docs: `agency_vocab.md`, `foia_codes.md`, `war_gov_quirks.md`. The whole thing is ~600 lines of Python and ~700 lines of Markdown.

## What the eval loop did

Four eval cases, each run twice — once with the skill, once without. 8 subagents in parallel. After grading and benchmarking:

| Eval | with skill | baseline | Δ |
|---|---|---|---|
| Full-tranche walkthrough | 100% | 60% | +40 |
| Single-file summary | 100% | 100% | 0 |
| Scanned-tranche honest caveats | 100% | 88% | +12 |
| Fresh-tranche bootstrap | 88% | 50% | +38 |
| **Mean** | **97%** | **74%** | **+23** |

Wall-clock: with-skill ran in ~12 min total; baseline took ~26 min. Tokens: with-skill 239K, baseline 259K. **The skill is faster, cheaper, and more accurate — except where the task is small enough that any competent agent nails it.** The single-file digest is the canonical example: an 8-page text-bearing PDF doesn't need a skill. A 4,000-page tranche with 64 scanned files does.

## Bugs the eval surfaced

1. **PNG/PDF wording bug.** The per-file digest emitted "(scanned/image PDF — OCR required)" for `.png` files. PNGs need vision analysis, not OCR. The eval-2 agent caught this by noticing the wording was sloppy in the FBI photo rows. Fixed: the summary function now branches on extension and inventory-side errors — scanned PDF, image file, or unreadable PDF each get their own message.
2. **ICAO airbase codes missing from vocab.** The d27 mission report's actual operational anchor is "OMAM" (Al Dhafra AB, UAE), not the UAE country name — but the skill's location list was country/region only. The eval-1 agent flagged this. Added OMAM, OMDB, OEDR, OBBI, OKBK, OAIX, LCRA, HEDC, HEMM. Skipped ORBI (Baghdad) because it collides with "orbit" in NASA mission text.
3. **Bootstrap response missed the agency-vocab extension workflow.** When asked "what's the fastest way to bootstrap release_02?", the skill answered with `run_all.py` and `war_gov_quirks.md` but not the OTHER-bucket-extension pattern. SKILL.md now surfaces this guidance explicitly in the bootstrap context.
4. **Turn-management: the original eval-0 agent backgrounded `extract_text.py` and ended its turn before the bash finished**, leaving a half-populated `text/` folder. SKILL.md now tells the agent to stay in the foreground and use the `[start] [end]` chunking pattern if a single call would actually time out — both finish quickly and the script is idempotent.

## What I'd skip if I did this again

The blind comparator agent. The four-eval setup with programmatic grading was sufficient signal — most failures were structural (missing reference, wrong file-type message, agent ended turn early), not ones a blind comparator would catch better than a regex.

## Where the skill earns its keep

Two places. First, in the "What's missing" section of REPORT.md — the part that names the 64 scanned files the analyzer can't read without OCR, the 1 file that errored on inventory, the heuristic limits of the entity extraction. That section is what makes the report honest. Without it, the report is a confident summary of half the data, which is worse than no summary. Second, in the bootstrap loop: when release_02 lands, `python scripts/run_all.py ~/UFO/release_02/` produces the same 11-section report the user already knows how to read. Repeatability beats novelty.

## Final score

96.9% with-skill, 74.4% baseline, +22.5 points. Skill is shipping.
