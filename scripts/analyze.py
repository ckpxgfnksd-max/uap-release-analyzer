#!/usr/bin/env python3
"""analyze.py <release_root>

Read inventory.csv + text/*.txt and write the analytics/ folder:
  top_terms.csv, terms_by_agency.csv, entities.json, per_file_digest.csv,
  cross_doc.json.

Entity surfacing here is keyword-list + regex. It's deliberately not full NER
— the goal is fast, transparent counts the user can audit. If you want NER,
run spaCy as a follow-up; this script is the always-on first pass.
"""
import csv, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

# ---------- vocab ----------
LOCATIONS = [
    "Iraq","Iran","Syria","Greece","Japan","Djibouti","Israel","Lebanon",
    "United Arab Emirates","UAE","Saudi Arabia","Kazakhstan","Papua New Guinea",
    "Pacific","Mediterranean","Arabian Gulf","Arabian Sea","Persian Gulf",
    "Strait of Hormuz","Gulf of Aden","Red Sea","East China Sea","Indo-Pacific",
    "INDOPACOM","CENTCOM","EUCOM","AFRICOM","Middle East","Western United States",
    "Africa","Europe","Asia","Russia","China","North Korea","Apollo","Skylab",
    "Gemini","Roswell","Washington","Pentagon",
    # ICAO airbase codes common in CENTCOM mission reports — these are operational
    # anchors (the actual takeoff/landing site) where country names rarely appear
    # in the body. Keep collision-free codes only; "ORBI" (Baghdad) is omitted
    # because it's a substring of "orbit" which appears in NASA mission text.
    "OMAM","OMDB","OEDR","OBBI","OKBK","OAIX","LCRA","HEDC","HEMM",
]
AGENCIES = ["FBI","DOW","DOD","DoD","ODNI","CIA","NSA","NASA","NRO","DOS","DIA",
            "AARO","DHS","FAA","NORAD","Navy","Air Force","Marine","Army"]
PHENOMENA = ["UAP","UFO","unidentified","anomalous","flying disc","craft","object",
             "sphere","orb","cylinder","disc","triangle","saucer","cigar","metallic",
             "tic-tac","tic tac"]
REDACTION_MARKERS = ["[REDACTED]","REDACTED","(REDACTED)","NOFORN","SECRET//NOFORN",
                     "TOP SECRET","/NOFORN","CLASSIFIED","UNCLASSIFIED//FOUO",
                     "UNCLASSIFIED//CUI","//CUI","REL TO USA","FOUO","CUI"]
# (b)(N) and (b) (N) variants — count via regex
BBOX_RE = re.compile(r"\(b\)\s?\((\d)\)")

STOPWORDS = set("""
a about above after again against all am an and any are as at be because been before being
below between both but by can could did do does doing don during each few for from further
had has have having he her here hers herself him himself his how i if in into is it its
itself just me more most my myself no nor not now of off on once only or other our ours
ourselves out over own same she should so some such t than that the their theirs them
themselves then there these they this those through to too under until up very was we were
what when where which while who whom why will with you your yours yourself yourselves would
""".split())
STOPWORDS |= {"unclassified","secret","redacted","cui","fouo","noforn","controlled","page",
              "from","with","this","that","also","which","they","them","their","said"}

WORD = re.compile(r"[A-Za-z][A-Za-z'\-]{2,}")
PROPER = re.compile(r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,}){1,3}\b")
YEAR = re.compile(r"\b(19[3-9]\d|20[0-3]\d)\b")


# --- prefix → agency (mirror of inventory.py) ----------
PREFIX_RULES = [
    (("65_hs1","fbi-photo","usper-","serial","2024-04-30-"), "FBI"),
    (("dow-uap","western_us_event"), "DOW"),
    (("nasa-uap",), "NASA"),
    (("dos-uap","059uap"), "DOS"),
    (("18_","38_","59_","255_","255-T-","331_","341_","342_"), "NARA"),
]
def agency_of(name: str) -> str:
    n = name.lower()
    for prefixes, a in PREFIX_RULES:
        if any(n.startswith(p) for p in prefixes):
            return a
    return "OTHER"


def find_release_dirs(root: Path):
    children = [p for p in root.iterdir() if p.is_dir() and p.name.lower().startswith("release_")]
    return sorted(children) if children else [root]


def tokens(text: str):
    for m in WORD.finditer(text):
        w = m.group(0).lower()
        if len(w) < 3 or w in STOPWORDS:
            continue
        yield w


def find_keywords(text: str, vocab):
    out = Counter()
    low = text.lower()
    for term in vocab:
        n = low.count(term.lower())
        if n:
            out[term] += n
    return out


def find_redactions(text: str):
    out = Counter()
    for m in REDACTION_MARKERS:
        n = text.count(m)
        if n:
            out[m] += n
    for d in BBOX_RE.findall(text):
        out[f"(b)({d})"] += 1
    return out


def summarize(text: str, name: str = "", pages_field: str = "", max_chars: int = 600) -> str:
    """Build a per-file summary.

    For files without extractable text, return a status message that names the
    *real* reason content is unavailable — distinguishing scanned PDFs (OCR
    needed), image files like PNG/JPG (vision analysis, not OCR), and
    structurally unreadable PDFs (pypdf couldn't open them at all). The right
    follow-up tool differs in each case, so the digest shouldn't lump them
    together under one generic "OCR required" label.
    """
    if not text.strip():
        ext = Path(name).suffix.lower() if name else ""
        if ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
            return "(image file — no text to extract; use vision analysis, not OCR)"
        # If inventory captured a pypdf error for this file, it's structurally
        # unreadable rather than scanned. Surface that distinction.
        if pages_field and isinstance(pages_field, str) and pages_field.startswith("ERR:"):
            return f"(unreadable PDF — pypdf {pages_field}; needs manual inspection)"
        if ext == ".pdf":
            return "(scanned PDF — no text layer; OCR required for content)"
        return "(no text — file type unknown)"
    head = text[:3000].replace("\n", " ").replace("\r", " ")
    head = re.sub(r"\s+", " ", head).strip()
    sents = re.split(r"(?<=[.!?])\s+", head)
    sents = [s.strip() for s in sents if 30 <= len(s) <= 220]
    return (" ".join(sents[:3]) if sents else head)[:max_chars]


def main(release_root: str) -> int:
    root = Path(release_root).expanduser().resolve()
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        return 2

    text_dir = root / "text"
    if not text_dir.is_dir():
        print(f"No text/ dir under {root} — run extract_text.py first", file=sys.stderr)
        return 2
    out_dir = root / "analytics"
    out_dir.mkdir(exist_ok=True)

    # gather files + matching text
    files = []
    for rel in find_release_dirs(root):
        files.extend(sorted(p for p in rel.iterdir() if p.is_file()))

    texts = {}
    for p in files:
        if p.suffix.lower() != ".pdf":
            texts[p.name] = ""
            continue
        tx = text_dir / (p.stem + ".txt")
        texts[p.name] = tx.read_text(errors="ignore") if tx.exists() else ""

    # Load inventory.csv so we can distinguish scanned PDFs from structurally
    # unreadable ones (pypdf error) when the .txt is empty/missing.
    pages_by_file: dict[str, str] = {}
    inv_path = root / "inventory.csv"
    if inv_path.exists():
        with open(inv_path, newline="") as f:
            for row in csv.DictReader(f):
                pages_by_file[row["filename"]] = str(row.get("pages", ""))

    # --- aggregate ---
    global_tok = Counter()
    per_agency_tok = defaultdict(Counter)
    per_file_tok = {}
    g_loc = Counter(); g_agen = Counter(); g_phen = Counter()
    g_year = Counter(); g_proper = Counter()
    per_file = {n: {} for n in texts}
    redaction_global = Counter()
    per_file_red = defaultdict(Counter)
    name_present = defaultdict(set)

    for name, t in texts.items():
        a = agency_of(name)
        c = Counter(tokens(t)); per_file_tok[name] = c
        global_tok.update(c); per_agency_tok[a].update(c)
        if not t.strip():
            # Even with no text, write the status message so per_file_digest.csv
            # tells the user *why* (scanned PDF / image / unreadable) instead of
            # leaving the row blank.
            per_file[name] = {"summary": summarize(t, name, pages_by_file.get(name, ""))}
            continue
        loc = find_keywords(t, LOCATIONS); agen = find_keywords(t, AGENCIES)
        phen = find_keywords(t, PHENOMENA); red = find_redactions(t)
        years = Counter(YEAR.findall(t))
        propers = Counter(PROPER.findall(t))
        per_file[name] = {"locations": loc, "agencies": agen, "phenomena": phen,
                          "years": years, "redactions": red,
                          "summary": summarize(t, name, pages_by_file.get(name, ""))}
        g_loc += loc; g_agen += agen; g_phen += phen
        g_year += years; g_proper += propers
        redaction_global += red; per_file_red[name] = red
        for nm in propers:
            name_present[nm].add(name)

    # --- top_terms.csv ---
    with open(out_dir / "top_terms.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["term","count"])
        for term, n in global_tok.most_common(200):
            w.writerow([term, n])

    # --- terms_by_agency.csv ---
    with open(out_dir / "terms_by_agency.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["agency","rank","term","count"])
        for a in sorted(per_agency_tok):
            for i, (t, n) in enumerate(per_agency_tok[a].most_common(40), 1):
                w.writerow([a, i, t, n])

    # --- entities.json ---
    multi_file_names = {nm: sorted(fs) for nm, fs in name_present.items() if len(fs) >= 5}
    entities = {
        "locations_global": g_loc.most_common(40),
        "agencies_global":  g_agen.most_common(40),
        "phenomena_global": g_phen.most_common(40),
        "year_clusters_top": sorted(g_year.items(), key=lambda x:-x[1])[:25],
        "names_in_5plus_files": dict(list(sorted(multi_file_names.items(), key=lambda x:-len(x[1])))[:60]),
    }
    with open(out_dir / "entities.json", "w") as f:
        json.dump(entities, f, indent=2)

    # --- per_file_digest.csv ---
    with open(out_dir / "per_file_digest.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["filename","agency","top_terms","top_locations","top_agencies",
                    "top_phenomena","redactions","summary"])
        for name in sorted(texts):
            a = agency_of(name)
            top = ", ".join(f"{t}({n})" for t,n in per_file_tok[name].most_common(8))
            d = per_file.get(name, {})
            locs = ", ".join(f"{l}({n})" for l,n in (d.get("locations") or Counter()).most_common(6))
            ags  = ", ".join(f"{l}({n})" for l,n in (d.get("agencies")  or Counter()).most_common(6))
            phs  = ", ".join(f"{l}({n})" for l,n in (d.get("phenomena") or Counter()).most_common(6))
            red  = ", ".join(f"{l}({n})" for l,n in (d.get("redactions") or Counter()).most_common(4))
            w.writerow([name, a, top, locs, ags, phs, red, d.get("summary","")])

    # --- cross_doc.json ---
    chars_by_agency = {a: sum(len(texts[n]) for n in texts if agency_of(n) == a)
                       for a in {"FBI","DOW","NARA","NASA","DOS","OTHER"}}
    cross = {
        "redaction_global": redaction_global.most_common(20),
        "files_with_most_redactions": sorted(
            ((n, sum(c.values())) for n, c in per_file_red.items()), key=lambda x:-x[1])[:15],
        "year_clusters_top": entities["year_clusters_top"],
        "files_per_agency_total_chars": chars_by_agency,
        "scanned_count": sum(1 for n,t in texts.items() if not t.strip() and Path(n).suffix.lower() == ".pdf"),
        "text_count":   sum(1 for t in texts.values() if t.strip()),
    }
    with open(out_dir / "cross_doc.json", "w") as f:
        json.dump(cross, f, indent=2)

    # --- summary to stdout ---
    print(f"Files in corpus: {len(texts)}")
    print(f"Text-bearing: {cross['text_count']}  Scanned (no text): {cross['scanned_count']}")
    print(f"Top locations:  {g_loc.most_common(5)}")
    print(f"Top phenomena:  {g_phen.most_common(5)}")
    print(f"Top agencies:   {g_agen.most_common(5)}")
    print(f"Top redactions: {redaction_global.most_common(5)}")
    print(f"Wrote analytics to {out_dir}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: analyze.py <release_root>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
