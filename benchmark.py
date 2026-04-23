"""Benchmark single-page vs batch, and compare server vs mobile rec."""
import os
import time
from pathlib import Path
from paddleocr import PPStructureV3

WORK_DIR = os.environ.get("WORK_DIR", "/tmp/book-convert")

PAGES_DIR = Path(f"{WORK_DIR}/pages")
sample = [1, 10, 50, 150, 200]

def bench(name, **kwargs):
    print(f"\n=== {name} ===", flush=True)
    t0 = time.time()
    p = PPStructureV3(
        use_seal_recognition=False,
        use_formula_recognition=False,
        use_chart_recognition=False,
        use_table_recognition=False,
        **kwargs,
    )
    print(f"init: {time.time()-t0:.1f}s")
    times = []
    for pnum in sample:
        img = PAGES_DIR / f"page-{pnum:03d}.png"
        t1 = time.time()
        results = p.predict(str(img))
        for r in results:
            _ = r.markdown if hasattr(r, "markdown") else str(r)
        dt = time.time() - t1
        times.append(dt)
    avg = sum(times)/len(times)
    print(f"per page: {times}")
    print(f"avg: {avg:.2f}s → 294p = {avg*294/60:.1f} min")
    return avg

a = bench("server det + server rec + unwarping",
          text_detection_model_name="PP-OCRv5_server_det",
          text_recognition_model_name="PP-OCRv5_server_rec")
b = bench("server det + server rec NO unwarping",
          text_detection_model_name="PP-OCRv5_server_det",
          text_recognition_model_name="PP-OCRv5_server_rec",
          use_doc_unwarping=False)
c = bench("mobile det + mobile rec + unwarping",
          text_detection_model_name="PP-OCRv5_mobile_det",
          text_recognition_model_name="PP-OCRv5_mobile_rec")
d = bench("mobile det + mobile rec NO unwarping",
          text_detection_model_name="PP-OCRv5_mobile_det",
          text_recognition_model_name="PP-OCRv5_mobile_rec",
          use_doc_unwarping=False)

print(f"\n{'config':<45} {'avg':>8} {'294p':>10}")
print(f"{'server+unwarp':<45} {a:>7.2f}s {a*294/60:>8.1f}m")
print(f"{'server no-unwarp':<45} {b:>7.2f}s {b*294/60:>8.1f}m")
print(f"{'mobile+unwarp':<45} {c:>7.2f}s {c*294/60:>8.1f}m")
print(f"{'mobile no-unwarp':<45} {d:>7.2f}s {d*294/60:>8.1f}m")
