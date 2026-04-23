---
name: pdf-to-epub
description: "Convert a scanned PDF (Chinese or English, primarily optimized for Chinese) into a clean EPUB with native footnotes, chapter navigation, and embedded image plates. TRIGGER when the user wants to convert a scanned PDF / DuXiu scan / 扫描版书籍 into EPUB, or mentions a PDF of a book (particularly Chinese) that isn't searchable. Signal phrases: 'convert this PDF to EPUB', '把这个PDF转成EPUB', 'turn this book into an EPUB', 'OCR this book', 'make this scanned book readable on my Kindle/iPad'. Also triggers for `/pdf-to-epub <path>`. Runs PaddleOCR PP-StructureV3 layout analysis + text recognition, infers book structure (chapters, footnotes, front-matter) from the OCR output, and packages with pandoc. NOT for: converting digital (text-layer) PDFs — those should use `pandoc` directly or `markitdown` + `pandoc`; extracting a single page or figure; generating a PDF from EPUB (reverse direction)."
version: 1.0.0
author: Yuhan Wang
license: MIT
tags: [pdf, epub, ocr, chinese, paddleocr, pandoc]
---

Convert a scanned-image PDF into a clean EPUB: OCR with layout analysis, structural cleanup driven by a per-book config, and pandoc for packaging.

## Arguments

`/pdf-to-epub <pdf_path> [output_epub_path]`

- `pdf_path` — required. Path to the scanned PDF.
- `output_epub_path` — optional. Defaults to the PDF path with `.epub` extension in `~/Downloads/`.

If the user invokes the skill in free-form (e.g. "convert this book"), ask for the PDF path.

## Why this skill exists

Scanned Chinese PDFs have recurring structural problems that pure-OCR pipelines don't solve:
- Vertical side-margin text (running book/chapter titles) that OCR reads as random single CJK characters inside paragraphs.
- Page headers/footers that look identical to chapter markers ("第一章" on every page of chapter 1).
- Footnotes anchored by a `*` in the main text — OCR preserves the `*` but doesn't link it to the footnote body at the page bottom.
- Paragraphs broken at page boundaries — the last 2 characters of a sentence on page N and the first 3 characters on page N+1 become separate "paragraphs" unless you join them.
- Image plates with OCR'd captions duplicated elsewhere.
- Publisher metadata (CIP data, ISBN, copyright, editorial committee) crammed together with no paragraph breaks.

The scripts handle the mechanical parts (OCR, pandoc). The skill body is about reading the OCR output and producing a `book_config.json` that tells `build_epub.py` what's a chapter vs. a page header vs. a front-matter section in *this specific book*.

## Pipeline overview

```
PDF
 │ pdftoppm -r 200
 ▼
pages/*.png
 │ ocr_structure.py  (PP-StructureV3 server models, layout-aware)
 ▼
structure_json/*.json + md_parts/*.md    ← per-page, resumable
 │ ocr_mobile_tail.py                    ← fast mobile fallback for any missing
 ▼                                          pages (server OCR leaks memory after ~250 pages)
md_parts/ (complete)
 │ assemble.py
 ▼
hilbert.md              (one big markdown)
 │ build_epub.py + book_config.json       ← ⭐ YOU generate this config
 ▼
hilbert_clean.md
 │ pandoc
 ▼
output.epub
```

## Steps

### Step 0 — Pre-flight dependency check

```bash
python3 skills/pdf-to-epub/scripts/check_deps.py
```

Verifies PaddleOCR packages, pandoc/poppler/imagemagick CLIs, and disk headroom for the model cache. If anything is missing it prints exact install commands and exits non-zero — relay the output to the user and stop until they install.

### Step 1 — Set up work directory

Use a fresh directory per book so intermediate artifacts don't collide:

```bash
export WORK_DIR=/tmp/pdf-epub-<book-slug>
export OUTPUT_EPUB=<output_epub_path>
mkdir -p "$WORK_DIR"
```

### Step 2 — Render pages

```bash
mkdir -p "$WORK_DIR/pages"
pdftoppm -r 200 -png "<pdf_path>" "$WORK_DIR/pages/page"
```

Check page count: `ls "$WORK_DIR/pages" | wc -l`. Expected: the PDF's total page count. If `pdftoppm` produces noticeably fewer, warn the user — some PDFs contain only a subset of pages (Anna's Archive / DuXiu scans occasionally have "pdg_main_pages_found < total_pages").

### Step 3 — OCR (long-running)

**Run the server-model OCR in the background**, monitor progress, and caffeinate the Mac so it doesn't sleep:

```bash
cd skills/pdf-to-epub/scripts
python3 ocr_structure.py &
OCR_PID=$!
caffeinate -s -w $OCR_PID &
disown
```

Expected speed: **~18–20 seconds per page** with server models + layout + doc-unwarping (benchmarked on Apple Silicon, CPU only). A 300-page book takes ~90 minutes.

**Known failure mode:** `PPStructureV3` has a memory leak that balloons to 20+ GB after ~250 pages, causing pages to take 30+ min each. If progress stalls (a single page taking >5 min, or per-page rate dropping below 0.02 pg/s), **kill the process** and run `ocr_mobile_tail.py` to finish the remaining pages with mobile models. The per-page JSONs are preserved, so no work is lost.

```bash
# Only if server OCR got stuck on the tail
python3 rebuild_md_from_json.py   # rebuild MD fragments from saved JSONs
python3 ocr_mobile_tail.py        # fill in pages still missing
```

Models auto-download on first run (~1.3 GB total) to `~/.paddlex/official_models/`. If the download is slow, see the progress in the log — `Fetching 6 files: 100%` means one model set done.

### Step 4 — Assemble one markdown

```bash
python3 assemble.py   # concatenates md_parts/*.md → $WORK_DIR/hilbert.md
```

(The filename `hilbert.md` is a historical default; use whatever — `book_config.json` can override via `source_md`.)

### Step 5 — Analyze the book and generate `book_config.json`

This is the creative part. Read the assembled MD and produce `$WORK_DIR/book_config.json`. See `references/book-config-schema.md` for the full schema.

What to look for when reading the assembled MD:

1. **Title, author, translator** — usually on the first 1–3 pages. Populate the metadata fields.
2. **TOC page** — usually within the first 20 pages. Look for a dense cluster of `第N章 <title>` entries. Copy the chapter numbers and titles exactly into `chapter_titles` (keyed by integer). Set `chapter_count` to the highest number.
3. **Running headers** — grep for the title words repeating on their own line. Common patterns: the book's short title and its subtitle alternating on left/right pages. Add them to `running_headers`.
4. **Image-plate range** — scan the first ~50 pages for runs of pages with `<50` CJK characters of OCR output. Those are photo plates. Set `image_plate_range: [lo, hi]`.
5. **Front-matter sections** — look for blocks like `出版说明`, `内容简介`, `作者简介`, `译者序`, `重读《...》之遐想`, `初版前言`, `前言`. These are often glued to the start of a paragraph instead of being real headings. For each, add a `heading_promotions` rule with a regex that matches the run-together form. Use the paragraph's first ~10 characters as the regex anchor (e.g. `^出版说明(?=自中西文明)` — match "出版说明" only when followed by the known first few characters of its body).
6. **Back-matter sections** — `后记`, `译者后记`, `附录`. Same treatment.
7. **Garbled TOC leftovers** — the TOC OCR often produces one or two unreadable lines that survive cleanup. Add them to `drop_patterns`.
8. **Trailer** — DuXiu/Anna's Archive PDFs have a metadata JSON on the last page. Check `trailer_markers` (default handles Anna's Archive).

**Reference the existing `sample/hilbert-book-config.json` as a fully worked example.** The Hilbert biography exercised almost every schema field.

### Step 6 — Build the EPUB

```bash
BOOK_CONFIG="$WORK_DIR/book_config.json" python3 build_epub.py
```

This:
- Cleans the markdown per the config (drops noise, promotes headings, detects chapters, attaches footnotes at inline `*` markers or falls back to end-of-paragraph).
- Writes `$WORK_DIR/<output_md>`.
- Invokes pandoc with `--split-level=2` to one EPUB file per chapter.
- Writes to `$OUTPUT_EPUB`.

### Step 7 — Audit

```bash
python3 audit.py       # summary: chapter count, footnote count, image count
python3 deep_audit.py  # scans for common OCR error patterns
```

Surface findings to the user:
- If `audit.py` reports fewer chapters than `chapter_count` in the config, a chapter boundary was missed. Check the raw MD for that chapter number — might need a chapter-pattern tweak.
- If footnote references ≠ definitions, some footnote didn't attach. The most common cause is OCR losing the inline `*`. You can either accept the fallback (end-of-paragraph attachment) or manually move the marker by editing the clean MD and rerunning pandoc.

### Step 8 — Open for review

```bash
open -a "Books" "$OUTPUT_EPUB"
```

Iterate on `book_config.json` based on user feedback. Rerunning `build_epub.py` only takes seconds; you don't need to re-OCR.

## Common follow-up fixes

Users typically spot issues by reading the first few chapters in Books. Common fixes:

| Symptom | Fix in config |
|---------|--------------|
| Stray single-char "乱码" in paragraphs | Add to `running_headers` if it's a repeating title char; otherwise the `is_single_cjk` filter already drops it. |
| Chapter N has wrong title or missing title | Edit `chapter_titles[N]`. |
| Heading duplicated (two chapters both called "第N章") | A page header was promoted. Tighten `chapter_pattern` or reduce `chapter_count`. |
| Footnote marker attached to wrong word | OCR lost the inline `*`. Either accept the fallback or add a book-specific regex. |
| Front-matter section inlined with body | Add a `heading_promotions` rule. |
| Blank image where caption belongs | `image_plate_range` is too narrow; expand it. |
| Every page of a chapter has a stray "第一章" | Server OCR picked up the running header. Add `"第一章"` etc. to `running_headers` (or refine `chap_pattern` to also require a body after). |

## Tooling / dependencies

```
pip install 'paddlepaddle' 'paddleocr' 'paddlex[ocr]'
brew install pandoc poppler imagemagick
```

On Apple Silicon, CPU inference is the only option (no MPS support for PaddleOCR as of this writing). Server model is ~2.5× slower than mobile but significantly more accurate on Chinese punctuation and proper nouns — worth it.

## Files bundled with this skill

- `scripts/check_deps.py` — pre-flight check for pip packages and CLI tools
- `scripts/ocr_structure.py` — PP-StructureV3 OCR, resumable
- `scripts/ocr_mobile_tail.py` — mobile-model OCR for pages the server couldn't finish
- `scripts/rebuild_md_from_json.py` — regenerate MD fragments from saved JSONs (after a crash)
- `scripts/assemble.py` — concatenate per-page fragments into one MD
- `scripts/build_epub.py` — config-driven cleanup + pandoc
- `scripts/audit.py`, `scripts/deep_audit.py` — post-build QA
- `scripts/benchmark.py` — optional: benchmark OCR configs on 5 sample pages
- `references/book-config-schema.md` — field-by-field schema for `book_config.json`
