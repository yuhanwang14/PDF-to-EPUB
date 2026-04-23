"""OCR all rendered pages with PaddleOCR v5 mobile models."""
import os
import sys
import time
from pathlib import Path
from paddleocr import PaddleOCR

WORK_DIR = os.environ.get("WORK_DIR", "/tmp/book-convert")

PAGES_DIR = Path(f"{WORK_DIR}/pages")
OUT_MD = Path(f"{WORK_DIR}/hilbert.md")
OUT_LOG = Path(f"{WORK_DIR}/ocr.log")

print("Loading PaddleOCR...", flush=True)
t0 = time.time()
ocr = PaddleOCR(
    text_detection_model_name="PP-OCRv5_mobile_det",
    text_recognition_model_name="PP-OCRv5_mobile_rec",
    use_textline_orientation=False,
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
)
print(f"Loaded in {time.time()-t0:.1f}s", flush=True)

pages = sorted(PAGES_DIR.glob("page-*.png"))
total = len(pages)
print(f"OCR starting: {total} pages", flush=True)

def order_text(res):
    """Return lines in reading order (top-to-bottom, left-to-right),
    dropping vertical-running side text that's typical for book headers/footers."""
    texts = res.get("rec_texts", [])
    scores = res.get("rec_scores", [])
    boxes = res.get("rec_boxes", None)
    polys = res.get("rec_polys", None)

    items = []
    for i, (t, s) in enumerate(zip(texts, scores)):
        if s < 0.5 or not t.strip():
            continue

        # Try to compute bounding box from rec_boxes or rec_polys
        x1 = y1 = x2 = y2 = 0
        try:
            if boxes is not None and i < len(boxes):
                x1, y1, x2, y2 = boxes[i][:4]
            elif polys is not None and i < len(polys):
                poly = polys[i]
                xs = [p[0] for p in poly]
                ys = [p[1] for p in poly]
                x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
        except Exception:
            pass

        w, h = x2 - x1, y2 - y1
        # Drop narrow vertical text (likely page header/footer running sideways)
        # Those have aspect ratio: height >> width AND very few chars per unit area
        if w > 0 and h > 0 and h / max(w, 1) > 3 and len(t) > 2:
            continue

        items.append((y1, x1, t.strip()))

    # Sort by y then x
    items.sort()
    return [t for _, _, t in items]


with OUT_MD.open("w", encoding="utf-8") as out, OUT_LOG.open("w", encoding="utf-8") as log:
    out.write("# 希尔伯特 — 数学世界的亚历山大\n\n")
    out.write("*Constance Reid 著；袁向东 李文林 译*\n\n")

    t_start = time.time()
    for i, page_path in enumerate(pages, 1):
        try:
            result = ocr.predict(str(page_path))
        except Exception as e:
            log.write(f"ERROR page {i}: {e}\n")
            log.flush()
            continue

        out.write(f"\n<!-- page {i} -->\n\n")
        if result and len(result) > 0:
            lines = order_text(result[0])
            if lines:
                out.write("\n\n".join(lines))
                out.write("\n")
        out.flush()

        if i % 5 == 0 or i == total:
            elapsed = time.time() - t_start
            rate = i / elapsed
            eta = (total - i) / rate if rate > 0 else 0
            print(f"[{i}/{total}] {rate:.1f} pg/s  ETA {eta/60:.1f}m", flush=True)

print(f"Done in {(time.time()-t_start)/60:.1f}m", flush=True)
