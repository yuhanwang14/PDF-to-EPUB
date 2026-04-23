"""OCR remaining pages with mobile models (fast)."""
import os
import time
from pathlib import Path
from paddleocr import PaddleOCR

WORK_DIR = os.environ.get("WORK_DIR", "/tmp/book-convert")

PAGES_DIR = Path(f"{WORK_DIR}/pages")
MD_DIR = Path(f"{WORK_DIR}/md_parts")
MD_DIR.mkdir(exist_ok=True)

ocr = PaddleOCR(
    text_detection_model_name="PP-OCRv5_mobile_det",
    text_recognition_model_name="PP-OCRv5_mobile_rec",
    use_textline_orientation=False,
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
)

total = 294
remaining = [i for i in range(1, total + 1) if not (MD_DIR / f"page-{i:03d}.md").exists()]
print(f"remaining: {len(remaining)} pages", flush=True)

t0 = time.time()
for k, i in enumerate(remaining, 1):
    img = PAGES_DIR / f"page-{i:03d}.png"
    if not img.exists():
        continue
    result = ocr.predict(str(img))
    texts = []
    for r in result:
        if "rec_texts" in r:
            for t, s in zip(r["rec_texts"], r["rec_scores"]):
                if s > 0.5 and t.strip():
                    texts.append(t.strip())
    md = "\n\n".join(texts)
    (MD_DIR / f"page-{i:03d}.md").write_text(md, encoding="utf-8")
    if k % 5 == 0 or k == len(remaining):
        rate = k / (time.time() - t0)
        print(f"[{i}/{total}] {rate:.1f} pg/s", flush=True)

print(f"done in {(time.time()-t0)/60:.1f}m", flush=True)
