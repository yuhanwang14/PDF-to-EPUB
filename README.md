# pdf-to-epub

Convert scanned Chinese (or other-language) PDFs into clean EPUBs with OCR, native EPUB footnotes, chapter navigation, and embedded image plates. Built on PaddleOCR PP-StructureV3 + pandoc.

Ships as a Claude Code plugin — installable into Claude Code and invoked via `/pdf-to-epub <pdf_path>` or natural language ("convert this PDF to EPUB").

## Why

Scanned Chinese PDFs from services like DuXiu / Anna's Archive have recurring structural problems that pure-OCR pipelines don't solve:

- Vertical side-margin text (running book/chapter titles) appears as isolated CJK characters inside paragraphs.
- Page headers/footers look identical to chapter markers (every page of chapter 1 has "第一章").
- Footnote markers (`*`) survive OCR but don't link to their body text at the page bottom.
- Paragraphs split at page boundaries become separate "paragraphs" unless explicitly rejoined.
- Publisher metadata is crammed into one giant paragraph with no breaks.

The deterministic scripts handle OCR and pandoc. The skill's SKILL.md tells Claude how to read the OCR output and produce a `book_config.json` that encodes the structural judgments (chapter titles, running headers, front-matter sections) for *this specific book*.

## Structure

```
pdf-to-epub/
├── .claude-plugin/plugin.json    Claude Code plugin manifest
├── skills/pdf-to-epub/
│   ├── SKILL.md                  Invocation instructions for Claude
│   ├── references/
│   │   └── book-config-schema.md  Schema for book_config.json
│   └── scripts/
│       ├── ocr_structure.py      PP-StructureV3 (server models), resumable
│       ├── ocr_mobile_tail.py    Mobile-model fallback for tail pages
│       ├── rebuild_md_from_json.py
│       ├── assemble.py
│       ├── build_epub.py         Config-driven cleanup + pandoc
│       ├── audit.py, deep_audit.py   Post-build QA
│       └── benchmark.py
└── sample/
    ├── sample-hilbert.pdf        15 MB, DuXiu scan
    ├── sample-hilbert.epub       2.4 MB, pipeline output
    └── hilbert-book-config.json  Worked example of every schema field
```

## Quick run (without Claude)

```bash
export WORK_DIR=/tmp/my-book
export OUTPUT_EPUB=~/Downloads/my-book.epub
export BOOK_CONFIG=$WORK_DIR/book_config.json

mkdir -p "$WORK_DIR/pages"
pdftoppm -r 200 -png sample/sample-hilbert.pdf "$WORK_DIR/pages/page"

cd skills/pdf-to-epub/scripts
python3 ocr_structure.py     # ~90 min for 300 pages, resumable
python3 assemble.py

# Hand-author or copy from sample/hilbert-book-config.json
cp ../../../sample/hilbert-book-config.json "$BOOK_CONFIG"

python3 build_epub.py
```

## With Claude

```
/pdf-to-epub sample/sample-hilbert.pdf
```

Claude runs OCR, reads the assembled markdown, infers the book's structure (TOC, chapters, running headers, image-plate range, front-matter sections), writes a per-book `book_config.json`, builds the EPUB, runs audits, and iterates if the user spots issues.

## Dependencies

```
pip install 'paddlepaddle' 'paddleocr' 'paddlex[ocr]'
brew install pandoc poppler imagemagick
```

First OCR run downloads ~1.3 GB of models to `~/.paddlex/official_models/`.

## Known limitations

- `PPStructureV3` has a memory leak that degrades speed after ~250 pages. The pipeline detects this and falls back to mobile OCR for the remainder.
- Math typography in the source PDF often survives as stray `$...$` or `{}` tokens in the OCR — these render as literal text, not rendered math.
- Footnote markers only anchor precisely if OCR preserved the inline `*`. When lost, they fall back to end-of-paragraph attachment, which is close but occasionally a word off.

## License

MIT. Sample PDF is a DuXiu scan of a public-domain-era work; redistribute at your discretion.
