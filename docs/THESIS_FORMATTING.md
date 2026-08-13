# Thesis Formatting Requirements (BS Computer Science)

**Source of truth:** `05_SOC Research Manual_May 2025 revision.docx` and
`SOC-Official-Template-Preliminaries.docx`, both in
`C:\Users\Kiyuk\Desktop\Thesis\Template`. These are the two files
confirmed to be for BS Computer Science specifically.

**Deliberately NOT used as a source here:**
`01_SOC Official Template Preliminary pages.docx` and
`02_SOC Official Template Body.docx` are for a different program (BS
Information Technology, Web Development specialization — confirmed by
the approval-sheet wording in that file). Anything from those two files
that isn't independently confirmed by the Research Manual is left out of
this document on purpose, since one such mismatch (a "Trade-off" /
"Statistical Treatment of Data" subsection that turned out not to apply
to BSCS) already caused confusion earlier in this project — see
`JUSTIFICATION.md` if that context is useful.

---

## Two different formats, two different purposes

The Research Manual is explicit that **two separate formatted versions**
of the manuscript are required:

1. **APA 7th Edition** — for the hardbound copy (the actual thesis
   submission).
2. **ACM format** — a separate, much shorter journal-style version
   prepared for publication (school-based or external journal).

These are not the same document reformatted — ACM is capped at 5–6
pages plus a 1-page bio-note, a completely different scope than the full
APA manuscript. Don't conflate the two when checking "is this formatted
correctly" — check against whichever target applies.

---

## APA 7th Edition (hardbound thesis copy)

**Page setup:**
- White 8.5 × 11-inch paper
- Margins: 1 inch on top, bottom, and right; **1.5 inch on the left**
  (not a uniform 1-inch margin — the left margin is wider, presumably
  for binding)
- Bordered page design as prescribed in the Research Manual's own
  Appendix C (this is an image in the source docx, not extractable as
  text — the live Google Doc already shows a red rectangular border on
  every page, which appears to already match this requirement, but
  worth a visual side-by-side check against the actual template image
  rather than assuming)

**Typography:**
- Font: Times New Roman, size 12, throughout
- Double-spaced, entire paper
- First word of every paragraph indented half an inch

**Required top-level components, in order:**
1. Title Page
2. Abstract
3. Main Body
4. References

**Full chapter/section structure** (per the Research Manual's BSCS
manuscript table and confirmed matching the live doc's actual outline):

- Abstract
- Introduction (includes problem statement)
- Review of Related Literature
- Conceptual or Theoretical Framework
- Objectives of the Study
- Scope and Delimitations
- Method
  - Research Design
  - Sources of Data (data sets and all relevant data sources)
  - Participants
  - Instruments
  - Data Collection
  - Data Analysis
  - Research Procedures
  - Ethical Consideration
- Results
- Discussion
  - Conclusion
  - Recommendations
- References
- Appendices

**Front matter** (from `SOC-Official-Template-Preliminaries.docx`):
- Cover Page
- Approval Sheet (adviser signature; Oral Examination section with panel
  chair + panel members; final Approval section signed by Program
  Chairperson and Dean)
- Acknowledgment (closes with "Laus Deo Semper!" — Holy Angel
  University's standard closing line)
- Table of Contents
- List of Tables
- List of Figures

**Appendices** (lettered, adjust as needed — per the template's own
note: "for the appendices E to M, adjust accordingly, you may add and
remove as necessary"):
- Appendix A — Cover Letter
- Appendix B — Interview Guide *(not applicable here — no interviews or
  volunteer participants in this study; skip or repurpose the letter)*
- Appendix C — Sample Instrument
- Appendix D — Use Case Diagram
- Appendix E — Current and Proposed Data Flow Diagram (if applicable)
- Appendix F — Entity Relationship Diagram (if applicable)
- Appendix G — Data Dictionary
- Appendix H — Gantt Chart
- Appendix I — Screenshots of Application
- Appendix J — Hardware and Software Specification
- Appendix K — Experts' Curriculum Vitae
- Appendix L — Editor's Note
- Appendix M — University Plagiarism Certificate
- Appendix N — Researchers' Curriculum Vitae

**List of Tables / List of Figures** (template examples, replace with
this study's actual tables/figures once Results exists):
- Table 1 — [Likert scale interpretation chart, if used]
- Table 2 — Dataset Distribution
- Figure 1 — Conceptual Framework
- Figure 2 — [any formula figures]
- Figure 3 — [any process/model diagram, e.g. CRISP-DM if illustrated]

---

## ACM format (separate journal-style submission)

**Scope:** 5–6 pages total, plus a separate 1-page bio-note. This is a
condensed version, not the full manuscript.

**Page setup:**
- Standard white 8.5 × 11-inch paper
- Margins: top/bottom/right 1 inch, left 1.5 inches (same asymmetric
  margin as APA)
- Paragraph: first line indented 0.5 inch, **1.5 line spacing** (not
  double-spaced like the APA version)

**Font table:**

| Component | Font | Size | Notes |
|---|---|---|---|
| Title | Times New Roman | 12pt | Bold |
| Author's Name | Times New Roman | 11pt | Ascending order by surname |
| Affiliation | Times New Roman | 9pt | |
| Abstract, CCS Concepts, Keywords | Times New Roman | 8pt | Keywords in bold |
| Headings | Times New Roman | 9pt | Numbered heading style |
| Subheadings | Times New Roman | 9pt | Sub-list numbering style |
| References Heading | Times New Roman | 9pt | |
| List of References | Times New Roman | 7pt | |
| About the Authors (heading) | Times New Roman | 9pt | Include a 1×1 inch photo; name in ALL CAPS |
| Bio-note | Times New Roman | 9pt (name) / 8pt (paragraph) | |
| Page Numbers | Times New Roman | 9pt | Center-aligned, bottom of page |

**Required sections, in order:**
1. Title and Author(s)
2. Introduction
3. Methodology
4. Results and Discussion
5. Conclusion and Recommendations
6. References
7. About the Authors

Note this collapses several APA chapters together (Results + Discussion
combined, Conclusion + Recommendations combined) — don't assume the ACM
version is just the APA version with formatting swapped; it needs its
own condensed writing pass once real Results content exists.

---

## Still to verify against the live doc

This document describes the *requirement*. It hasn't been checked
line-by-line against the live doc's actual formatting yet (only content
correctness has been checked so far, across `PAPER_EDITS_NEEDED.md`
items #1-9). Worth a dedicated pass on:

- [ ] Actual page margins (Google Docs Page Setup) match 1"/1"/1"/1.5"
      left
- [ ] Font is Times New Roman 12pt throughout, not just in the sections
      already spot-checked in this session
- [ ] Line spacing is double throughout the APA body (not just the
      sections read during content review)
- [ ] Paragraph indents are consistently 0.5 inch (one inconsistency —
      the Recommendations section's second paragraph missing its indent
      — was already caught and fixed manually)
- [ ] Border/page-frame design matches the Research Manual's Appendix C
      image (visual check, can't be done from extracted text)
- [ ] Front matter (Approval Sheet, Acknowledgment, ToC, List of Tables,
      List of Figures) exists and is filled in, not still template
      placeholder text
- [ ] Appendices lettering matches what this study actually has (drop
      Appendix B/Interview Guide since no interviews were conducted;
      confirm which of C–N actually apply)
- [ ] A separate ACM-format version exists or has been started — as of
      this writing, only the APA/hardbound version has been discussed in
      this project
