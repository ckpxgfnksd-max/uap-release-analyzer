# FOIA Exemptions and Classification Markers

What the redaction stamps in declassified UAP tranches mean. The analyzer
counts these per-file and surfaces the most-redacted documents. Knowing
*which* exemption is being invoked tells you something about *why* the
content was withheld.

## FOIA exemptions (5 USC 552(b))

| Code | Name | What it shields |
|---|---|---|
| `(b)(1)` | National security | Properly classified info — usually appears alongside SECRET / TOP SECRET banners. |
| `(b)(2)` | Internal personnel rules and practices | Rare in UAP material. |
| `(b)(3)` | Statutorily exempt | Withheld under another statute (NSA Act, 18 USC 798, etc.). Common in IC documents. |
| `(b)(4)` | Trade secrets / commercial | Rare in UAP material; appears in contractor docs. |
| `(b)(5)` | Deliberative process / privilege | Inter-agency drafts, attorney-client. |
| `(b)(6)` | Personal privacy | Names, addresses, witness IDs. **Dominates** modern mission reports. |
| `(b)(7)` | Law-enforcement records | FBI investigative material. Often `(b)(7)(C)` or `(b)(7)(E)`. |
| `(b)(8)` | Bank examination | n/a |
| `(b)(9)` | Geological / geophysical info | n/a |

## Classification banners

| Marker | Meaning |
|---|---|
| `UNCLASSIFIED` / `U` | Cleared for public release. |
| `UNCLASSIFIED//FOUO` | For official use only — withheld under a non-FOIA basis. |
| `UNCLASSIFIED//CUI` | Controlled unclassified information (post-EO 13556). |
| `CONFIDENTIAL` / `C` | Lowest classification tier. |
| `SECRET` / `S` | Default classification for current DOW UAP material. |
| `TOP SECRET` / `TS` | Highest tier; rare in releases. |
| `SECRET//NOFORN` | Secret + No Foreign nationals. |
| `//NOFORN` | Trailing dissemination control. |
| `REL TO USA` | Releasable only to U.S. nationals (or named partners — `REL TO USA, FVEY` etc.). |
| `ORCON` | Originator controls dissemination. |
| `IMCON` | Imagery control markings. |
| `EYES ONLY` | Restricted to named recipients. |

## What patterns mean

- **(b)(1) heavy + NOFORN heavy** → genuine national-security classification, modern operational reporting (DOW mission reports).
- **(b)(6) heavy + (b)(7)(C) heavy** → privacy-redacted investigative file (FBI).
- **REL TO USA** present → file shared inside coalition/intel partnerships, redacted before public release.
- **No markers, but heavily blacked out** → likely a pre-FOIA release or an older review without modern code annotations. The analyzer can't count those without OCR.

## What the analyzer counts

`analyze.py` matches:

- `[REDACTED]`, `(REDACTED)`, literal `REDACTED`
- `(b)(N)` and `(b) (N)` for N in 1–7
- Classification banners listed above (NOFORN, SECRET//NOFORN, etc.)

It does **not** count black redaction boxes or image-only stamps — those need OCR + visual inspection.
