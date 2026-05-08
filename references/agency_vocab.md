# Agency Filename Vocabulary

How files in declassified UAP tranches map to source agencies. Filename
prefixes are the load-bearing signal — the war.gov releases (and the FBI
Vault, NARA, AARO) all encode origin in the prefix.

When you see a prefix not in this list, classify as `OTHER` and surface it
to the user. If a new prefix appears repeatedly across a tranche, extend
this file rather than hard-coding into `analyze.py`.

## Established prefixes

| Prefix(es) | Agency | Notes |
|---|---|---|
| `65_hs1*` | FBI | HQ-series scanned case files. |
| `fbi-photo-a*` | FBI | PNG infrared images (A-series). |
| `fbi-photo-b*` | FBI | PDF-wrapped images (B-series). |
| `usper-*` | FBI | U.S.-person testimony, redacted. |
| `serial*`, `serial-*` | FBI | Re-redacted case-file serials. |
| `2024-04-30-*` | FBI | Composite sketches, dated prefix. |
| `dow-uap-*` | DOW | Department of War mission/range-fouler reports. |
| `western_us_event*` | DOW | DOW briefing decks. |
| `nasa-uap-d*` | NASA | Mission transcripts and crew debriefings. |
| `nasa-uap-vm*` | NASA | NASA visual material (JPGs). |
| `dos-uap-*` | DOS | State Department cables. |
| `059uap*` | DOS | NARA RG59 (State) UAP-tagged files. |
| `18_*` | NARA | RG18 — Records of the Army Air Forces. |
| `38_*` | NARA | RG38 — Office of the Chief of Naval Ops. |
| `59_*` | NARA | RG59 — General Records of the Department of State. |
| `255_*`, `255-T-*` | NARA | RG255 — Records of NASA. |
| `331_*` | NARA | RG331 — Allied Operational Forces, WWII. |
| `341_*` | NARA | RG341 — Records of HQ U.S. Air Force. |
| `342_*` | NARA | RG342 — Records of U.S. Air Force commands. |

## How to extend

When the analyzer surfaces an `OTHER` bucket of more than ~3% of a tranche,
inspect a few of those filenames, identify the issuing agency (often
discoverable from a cover page or the filename's date pattern), and add a
new row above. Then re-run `analyze.py` — agency rollups update
automatically.

## Caveats

- Some tranches re-use prefixes across agencies (e.g., `serial*` could be
  FBI or another agency that uses serial numbering). The current rules are
  tuned to the May 2026 war.gov tranche. When you see a serial-prefixed
  file from elsewhere, check the issuing-agency cover page.
- DOW (Department of War) is the post-2025 rename of what was formerly
  "DoD" / "Department of Defense". Both terms appear in text.
