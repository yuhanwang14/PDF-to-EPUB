"""PP-StructureV3 OCR with server models + layout + unwarping.

Disabled: seal, formula, chart, table (book has none).
Output: {WORK_DIR}/hilbert_structure.md
        {WORK_DIR}/structure_json/page-NNN.json
"""
import os
import sys
import time
from pathlib import Path
from paddleocr import PPStructureV3

WORK_DIR = os.environ.get("WORK_DIR", "/tmp/book-convert")

PAGES_DIR = Path(f"{WORK_DIR}/pages")
OUT_MD = Path(f"{WORK_DIR}/hilbert_structure.md")
OUT_JSON_DIR = Path(f"{WORK_DIR}/structure_json")
OUT_JSON_DIR.mkdir(exist_ok=True)

print("Loading PP-StructureV3 (server OCR + unwarping, no table/formula/seal)...", flush=True)
t0 = time.time()
pipeline = PPStructureV3(
    use_seal_recognition=False,
    use_formula_recognition=False,
    use_chart_recognition=False,
    use_table_recognition=False,
    # use_doc_unwarping default True → UVDoc corrects spine curvature
    text_detection_model_name="PP-OCRv5_server_det",
    text_recognition_model_name="PP-OCRv5_server_rec",
)
print(f"Loaded in {time.time()-t0:.1f}s", flush=True)

pages = sorted(PAGES_DIR.glob("page-*.png"))
total = len(pages)

# Resume: per-page markdown fragments go into md_parts/; a completed page
# has both page-NNN.json AND page-NNN.md. We process any missing pages
# and always reassemble OUT_MD from the fragments at the end.
MD_PARTS_DIR = Path(f"{WORK_DIR}/md_parts")
MD_PARTS_DIR.mkdir(exist_ok=True)

def is_done(i):
    return (OUT_JSON_DIR / f"page-{i:03d}.json").exists() and (MD_PARTS_DIR / f"page-{i:03d}.md").exists()

remaining = [(i, p) for i, p in enumerate(pages, 1) if not is_done(i)]
print(f"Total {total} pages, already done {total - len(remaining)}, remaining {len(remaining)}", flush=True)

t_start = time.time()
for k, (i, page_path) in enumerate(remaining, 1):
    try:
        results = pipeline.predict(str(page_path))
    except Exception as e:
        print(f"ERROR page {i}: {e}", flush=True)
        continue

    md_parts = []
    for res in results:
        try:
            json_path = OUT_JSON_DIR / f"page-{i:03d}.json"
            res.save_to_json(str(json_path))
            md_info = res.markdown
            md_text = md_info.get("markdown_texts", "") if isinstance(md_info, dict) else str(md_info)
            md_parts.append(md_text)
        except Exception as e:
            print(f"  serialize error page {i}: {e}", flush=True)
    (MD_PARTS_DIR / f"page-{i:03d}.md").write_text("\n".join(md_parts), encoding="utf-8")

    if k % 5 == 0 or k == len(remaining):
        elapsed = time.time() - t_start
        rate = k / elapsed
        eta = (len(remaining) - k) / rate if rate > 0 else 0
        print(f"[{i}/{total}] {rate:.2f} pg/s  ETA {eta/60:.1f}m", flush=True)

# Assemble final markdown from per-page fragments (always, so resume is safe)
with OUT_MD.open("w", encoding="utf-8") as out:
    out.write("# 希尔伯特 — 数学世界的亚历山大\n\n")
    out.write("*Constance Reid 著；袁向东 李文林 译*\n\n")
    for i in range(1, total + 1):
        frag = MD_PARTS_DIR / f"page-{i:03d}.md"
        out.write(f"\n<!-- page {i} -->\n\n")
        if frag.exists():
            out.write(frag.read_text(encoding="utf-8"))
            out.write("\n")

print(f"Done in {(time.time()-t_start)/60:.1f}m", flush=True)
