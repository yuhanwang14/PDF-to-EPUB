"""Assemble final markdown from per-page fragments (server + mobile)."""
from pathlib import os
import Path

WORK_DIR = os.environ.get("WORK_DIR", "/tmp/book-convert")

MD_DIR = Path(f"{WORK_DIR}/md_parts")
OUT = Path(f"{WORK_DIR}/hilbert.md")  # overwrite, same name as before

total = 294
with OUT.open("w", encoding="utf-8") as out:
    out.write("# 希尔伯特 — 数学世界的亚历山大\n\n")
    out.write("*Constance Reid 著；袁向东 李文林 译*\n\n")
    for i in range(1, total + 1):
        frag = MD_DIR / f"page-{i:03d}.md"
        out.write(f"\n<!-- page {i} -->\n\n")
        if frag.exists():
            out.write(frag.read_text(encoding="utf-8"))
            out.write("\n")

print(f"assembled {total} pages → {OUT}")
