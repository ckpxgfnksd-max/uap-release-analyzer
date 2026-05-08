#!/usr/bin/env python3
"""build_report.py <release_root>

Read inventory.csv + analytics/*.json|csv and write REPORT.md following the
standard 11-section structure documented in SKILL.md.
"""
import csv, json, sys
from collections import Counter
from pathlib import Path


SECTION_ORDER = [
    "1. Inventory",
    "2. What's actually in the release",
    "3. Where the activity is concentrated",
    "4. Phenomena terminology",
    "5. Agency cross-references",
    "6. Year clusters",
    "7. Redactions",
    "8. Notable individual files",
    "9. Cross-document patterns",
    "10. What's missing / caveats",
    "11. Files in this analysis",
]


def md_table(headers, rows):
    line = "| " + " | ".join(headers) + " |"
    sep  = "|" + "|".join("---" for _ in headers) + "|"
    body = "\n".join("| " + " | ".join(str(c) for c in r) + " |" for r in rows)
    return f"{line}\n{sep}\n{body}\n"


def main(release_root: str) -> int:
    root = Path(release_root).expanduser().resolve()
    inv_path = root / "inventory.csv"
    ana = root / "analytics"
    if not inv_path.exists() or not ana.is_dir():
        print(f"Need {inv_path} and {ana}/. Run inventory.py + analyze.py first.", file=sys.stderr)
        return 2

    inv = list(csv.DictReader(open(inv_path)))
    ent = json.load(open(ana / "entities.json"))
    cross = json.load(open(ana / "cross_doc.json"))

    # inventory rollups
    total = len(inv)
    bytes_total = sum(int(r["size_bytes"]) for r in inv)
    pdf_pages   = sum(int(r["pages"]) for r in inv if r["pages"].isdigit())
    pdfs = sum(1 for r in inv if r["ext"] == "pdf")
    pngs = sum(1 for r in inv if r["ext"] == "png")
    jpgs = sum(1 for r in inv if r["ext"] == "jpg")
    by_agency = Counter(r["agency"] for r in inv)

    out = []
    out.append("# Declassified UAP Release — Raw Analytics\n")
    out.append(f"**Files in this analysis:** {total}  ·  **Total size:** {bytes_total/1024/1024/1024:.2f} GB  ·  **Total PDF pages:** {pdf_pages:,}\n")

    # ---- 1. Inventory ----
    out.append(f"\n## 1. Inventory\n")
    out.append(md_table(["Metric", "Value"], [
        ["Files", total],
        ["Total size", f"{bytes_total/1024/1024/1024:.2f} GB"],
        ["Total PDF pages", f"{pdf_pages:,}"],
        ["PDFs", pdfs],
        ["PNGs", pngs],
        ["JPGs", jpgs],
        ["Files with text", cross["text_count"]],
        ["Files scanned (no text layer)", cross["scanned_count"]],
    ]))
    out.append("\n### By agency\n")
    out.append(md_table(["Agency", "Files", "Extracted text (chars)"], [
        [a, by_agency.get(a, 0), f"{cross['files_per_agency_total_chars'].get(a, 0):,}"]
        for a in ["FBI","DOW","NARA","NASA","DOS","OTHER"] if by_agency.get(a, 0)
    ]))

    # ---- 2. What's actually in the release ----
    out.append(f"\n## 2. What's actually in the release\n")
    buckets = []
    if by_agency.get("FBI"):  buckets.append(f"- **FBI** ({by_agency['FBI']} files): photos, case-file sections, redacted serials.")
    if by_agency.get("DOW"):  buckets.append(f"- **DOW** ({by_agency['DOW']} files): mission reports, range-fouler debriefs, email correspondence.")
    if by_agency.get("NASA"): buckets.append(f"- **NASA** ({by_agency['NASA']} files): mission transcripts, crew debriefings, visual material.")
    if by_agency.get("DOS"):  buckets.append(f"- **DOS** ({by_agency['DOS']} files): cables and embassy traffic.")
    if by_agency.get("NARA"): buckets.append(f"- **NARA** ({by_agency['NARA']} files): historical record-group boxes, often scanned-only.")
    if by_agency.get("OTHER"):buckets.append(f"- **OTHER** ({by_agency['OTHER']} files): unclassified prefix — review and possibly extend `agency_vocab.md`.")
    out.append("\n".join(buckets) or "_no data_")
    out.append("\n")

    # ---- 3. Locations ----
    out.append(f"\n## 3. Where the activity is concentrated\n")
    if ent["locations_global"]:
        out.append(md_table(["Location", "Mentions"],
                            [[l, n] for l, n in ent["locations_global"][:15]]))
    else:
        out.append("_no extractable text — locations would require OCR_\n")

    # ---- 4. Phenomena ----
    out.append(f"\n## 4. Phenomena terminology\n")
    if ent["phenomena_global"]:
        out.append(md_table(["Term", "Mentions"], ent["phenomena_global"][:15]))
    else:
        out.append("_no data_\n")

    # ---- 5. Agencies in text ----
    out.append(f"\n## 5. Agency cross-references\n")
    if ent["agencies_global"]:
        out.append(md_table(["Agency named in text", "Mentions"], ent["agencies_global"][:15]))
    else:
        out.append("_no data_\n")

    # ---- 6. Year clusters ----
    out.append(f"\n## 6. Year clusters\n")
    if ent["year_clusters_top"]:
        out.append(md_table(["Year", "Mentions"], ent["year_clusters_top"][:15]))
    else:
        out.append("_no extractable dates_\n")

    # ---- 7. Redactions ----
    out.append(f"\n## 7. Redactions\n")
    if cross["redaction_global"]:
        out.append(md_table(["Marker", "Hits"], cross["redaction_global"][:10]))
        out.append("\n### Files with the most redaction markers\n")
        for n, hits in cross["files_with_most_redactions"][:10]:
            out.append(f"- `{n}` — {hits}")
        out.append("\n")
    else:
        out.append("_no redaction markers detected (likely all-scanned tranche)_\n")

    # ---- 8. Notable files ----
    out.append(f"\n## 8. Notable individual files\n")
    inv_sorted = sorted(inv, key=lambda r: -int(r["size_bytes"]))[:5]
    for r in inv_sorted:
        out.append(f"- `{r['filename']}` — {r['agency']}, {r['size_mb']} MB, {r['pages']} pages")
    out.append("\nFor a full per-file digest see `analytics/per_file_digest.csv`.\n")

    # ---- 9. Cross-document patterns ----
    out.append(f"\n## 9. Cross-document patterns\n")
    out.append("- Geographic clustering by agency, temporal clustering, and recurring proper names "
               "are surfaced in `entities.json` and `cross_doc.json`. ")
    if ent["names_in_5plus_files"]:
        out.append("Names appearing across 5+ files: ")
        out.append(", ".join(list(ent["names_in_5plus_files"].keys())[:10]))
    out.append("\n")

    # ---- 10. Caveats ----
    out.append(f"\n## 10. What's missing / caveats\n")
    notes = []
    if cross["scanned_count"]:
        notes.append(f"- **OCR not run.** {cross['scanned_count']} files have no text layer. Run Tesseract as a follow-up if you need that content searchable.")
    notes.append("- Entity extraction is keyword-list + regex, not full NER. Re-run with spaCy if you need person/org disambiguation.")
    notes.append("- Year mentions ≠ incident dates. Filename suffixes (e.g. `...-strait-of-hormuz-september-2020.pdf`) are usually a more reliable date signal.")
    out.append("\n".join(notes))
    out.append("\n")

    # ---- 11. Files in this analysis ----
    out.append(f"\n## 11. Files in this analysis\n")
    out.append("- `inventory.csv` — full file inventory")
    out.append("- `text/` — extracted text per PDF")
    out.append("- `analytics/top_terms.csv` — top 200 terms")
    out.append("- `analytics/terms_by_agency.csv` — top 40 terms per agency")
    out.append("- `analytics/entities.json` — locations, agencies, phenomena, year clusters")
    out.append("- `analytics/per_file_digest.csv` — per-file top terms, locations, redactions, summary")
    out.append("- `analytics/cross_doc.json` — redaction patterns, year clusters, agency totals")
    out.append("\n")

    out_path = root / "REPORT.md"
    out_path.write_text("\n".join(out))
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: build_report.py <release_root>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
