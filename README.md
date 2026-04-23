# PDF to EPUB (Chinese scanned book)

Pipeline for converting DuXiu-scanned Chinese PDFs to clean EPUBs with OCR, native footnotes, and image plates.

Developed against: `希尔伯特 — 数学世界的亚历山大` (Constance Reid, 上海科学技术出版社 2006).

## Pipeline

```
PDF (scanned)
  │
  ▼  pdftoppm -r 200 → PNG per page
pages/*.png
  │
  ▼  ocr_structure.py (PP-StructureV3, server models)
  │    – layout analysis separates body/header/footer/footnote/image
  │    – per-page JSON + MD fragment
structure_json/page-NNN.json
md_parts/page-NNN.md
  │
  ▼  ocr_mobile_tail.py (mobile fallback for any missing pages)
  │    – server OCR tends to slow down on long runs (RAM leak),
  │      mobile is a fast fallback for the tail
  │
  ▼  assemble.py → hilbert.md (one big markdown)
  │
  ▼  make_epub.sh
  │    – drop vertical side-margin text, page numbers, headers
  │    – detect real chapter boundaries (use TOC title map to avoid
  │      garbled page-header "第N章" matches)
  │    – convert footnote bodies to native [^n] pandoc footnotes
  │    – anchor markers at inline `*` in OCR text
  │    – promote front-matter sections (出版说明, 内容简介, etc.)
  │    – embed photo-plate pages as JPEGs
  │
  ▼  pandoc --split-level=2 → final .epub
```

## Scripts

| File | Purpose |
|------|---------|
| `ocr_structure.py` | PP-StructureV3 OCR with resume support |
| `ocr_mobile_tail.py` | Fast mobile OCR for pages server couldn't finish |
| `ocr_pages.py` | Original simple mobile-only OCR (superseded) |
| `rebuild_md_from_json.py` | Regenerate MD fragments from saved PP-StructureV3 JSONs |
| `assemble.py` | Concatenate per-page MD fragments into a single `hilbert.md` |
| `make_epub.sh` | Clean up the combined MD and invoke pandoc |
| `benchmark.py` | Benchmark OCR configs (server vs mobile, unwarp on/off) |
| `audit.py` | Summary audit of the final EPUB (chapter count, footnote count, images) |
| `deep_audit.py` | Detailed OCR-error scan (OCR confusions, broken paragraphs, stray `$`) |

## Known limitations

- Server PP-StructureV3 has a memory leak that degrades speed after ~250 pages; resume from saved JSONs.
- OCR embeds stray `$...$` and `{}` where the source PDF had math typography — these come through as literal text.
- `*` footnote markers in OCR output only survive when they were typographically distinct in the scan; cases where the marker was lost fall back to appending at paragraph end.

## Usage

All scripts read `$WORK_DIR` (default `/tmp/book-convert`) and `$OUTPUT_EPUB` (default `$WORK_DIR/book.epub`).

```bash
export WORK_DIR=/tmp/my-book
export OUTPUT_EPUB=~/Downloads/my-book.epub

# 1. Render PDF pages to 200dpi PNGs
mkdir -p "$WORK_DIR/pages"
pdftoppm -r 200 -png sample/sample-hilbert.pdf "$WORK_DIR/pages/page"

# 2. Primary OCR (resumable — kill and restart if it hangs)
python3 ocr_structure.py

# 3. Fill any pages the server OCR skipped
python3 ocr_mobile_tail.py

# 4. Assemble per-page fragments, clean, package as EPUB
python3 assemble.py
bash make_epub.sh
```

Note: `make_epub.sh` still contains book-specific cleanup rules (hardcoded chapter titles for this Hilbert biography, front-matter heading patterns, OCR-artifact filters). Adapt it for your own book.

## Sample

`sample/sample-hilbert.pdf` (15 MB, DuXiu scan) → `sample/sample-hilbert.epub` (2.4 MB, pipeline output).

## Dependencies

```
pip install 'paddlepaddle' 'paddleocr' 'paddlex[ocr]'
brew install pandoc poppler imagemagick
```
