"""Detailed audit of the final EPUB content."""
import os
import re
from pathlib import Path

WORK_DIR = os.environ.get("WORK_DIR", "/tmp/book-convert")

TEXT_DIR = Path(f"{WORK_DIR}/epub-extract/EPUB/text")
CLEAN = Path(f"{WORK_DIR}/hilbert_clean.md")

print("=" * 60)
print("1. CHAPTER STRUCTURE")
print("=" * 60)
chapter_files = sorted(TEXT_DIR.glob("ch*.xhtml"))
for f in chapter_files:
    content = f.read_text(encoding="utf-8")
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", content)
    h2 = re.search(r"<h2[^>]*>(.*?)</h2>", content)
    paras = len(re.findall(r"<p>", content))
    chars = len(re.sub(r"<[^>]+>", "", content))
    imgs = len(re.findall(r"<img", content))
    heading = (h2 or h1).group(1) if (h2 or h1) else "(no heading)"
    heading = re.sub(r"<[^>]+>", "", heading)
    print(f"{f.name}: {heading[:40]:<40} {chars:>6}ch {paras:>3}p {imgs:>2}img")

print("\n" + "=" * 60)
print("2. FOOTNOTES")
print("=" * 60)
all_text = "\n".join(f.read_text(encoding="utf-8") for f in chapter_files)
fn_refs = re.findall(r'id="fnref(\d+)"', all_text)
fn_defs = re.findall(r'id="fn(\d+)"', all_text)
print(f"References: {len(fn_refs)}")
print(f"Definitions: {len(fn_defs)}")
orphaned_refs = set(fn_refs) - set(fn_defs)
orphaned_defs = set(fn_defs) - set(fn_refs)
if orphaned_refs:
    print(f"Orphan refs (no def): {orphaned_refs}")
if orphaned_defs:
    print(f"Orphan defs (no ref): {orphaned_defs}")
# Show distribution
fn_by_chapter = {}
for f in chapter_files:
    refs = re.findall(r'id="fnref(\d+)"', f.read_text(encoding="utf-8"))
    if refs:
        fn_by_chapter[f.name] = len(refs)
print("Footnotes per chapter:")
for ch, n in fn_by_chapter.items():
    print(f"  {ch}: {n}")

print("\n" + "=" * 60)
print("3. IMAGES")
print("=" * 60)
img_files = sorted(Path(f"{WORK_DIR}/epub-extract/EPUB/media").glob("*") if (Path(f"{WORK_DIR}/epub-extract/EPUB/media")).exists() else [])
if not img_files:
    # Try alternative paths
    for candidate in [f"{WORK_DIR}/epub-extract/EPUB/images", f"{WORK_DIR}/epub-extract"]:
        p = Path(candidate)
        if p.exists():
            img_files = list(p.rglob("*.jpg"))
            if img_files:
                break
print(f"Image files in EPUB: {len(img_files)}")
# Find <img src="..."> references
img_refs = re.findall(r'<img[^>]*src="([^"]*)"', all_text)
print(f"Image references: {len(img_refs)}")
print(f"Sample refs: {img_refs[:3]}")

print("\n" + "=" * 60)
print("4. CONTENT LENGTH CHECK")
print("=" * 60)
# Compute ratio of chars per chapter — anomalies (too short?)
sizes = []
for f in chapter_files:
    if f.name in ("ch001.xhtml",):
        continue
    content = f.read_text(encoding="utf-8")
    cjk = sum(1 for c in content if '一' <= c <= '鿿')
    sizes.append((f.name, cjk))
sizes.sort(key=lambda x: x[1])
print("Smallest chapters (by CJK count):")
for name, cjk in sizes[:5]:
    print(f"  {name}: {cjk} CJK chars")
print("Largest:")
for name, cjk in sizes[-3:]:
    print(f"  {name}: {cjk} CJK chars")

print("\n" + "=" * 60)
print("5. COMMON OCR ERROR PATTERNS")
print("=" * 60)
# Known OCR confusions in Chinese: 己vs已, 末vs未, 人vs入, 时vs旧
patterns = [
    ("易混字 人/入", r"[人入]"),
    ("断裂数字 (e.g. '1 23' instead of '123')", r"\d \d"),
    ("遗留侧边文字 (isolated single char between blanks)", r"\n\n[一-鿿]\n\n"),
    ("可疑的页眉重复", r"希尔伯特[^，。\n]{0,10}希尔伯特"),
    ("遗留译注标记", r"——译注|——-译注|—译注|译注"),
    ("数学表达式破损", r"\{\+|\^\{[^}]*$"),
]
for desc, pat in patterns:
    cnt = len(re.findall(pat, all_text))
    print(f"  {desc}: {cnt}")

print("\n" + "=" * 60)
print("6. SERVER→MOBILE OCR BOUNDARY (around page 266→267)")
print("=" * 60)
# Last chapter should have this transition
last_ch = chapter_files[-1]
text = last_ch.read_text(encoding="utf-8")
text_only = re.sub(r"<[^>]+>", "", text)
paras = [p.strip() for p in text_only.split("\n") if p.strip()]
print(f"Last chapter ({last_ch.name}) has {len(paras)} non-blank lines")
print("Last 10 paragraphs:")
for p in paras[-10:]:
    print(f"  {p[:100]}")

print("\n" + "=" * 60)
print("7. KNOWN LATEX ISSUES")
print("=" * 60)
# Look for ${...}$ or { ... } that pandoc might parse as LaTeX
latex_like = re.findall(r'[^\\]\$[^$]{2,50}\$', all_text)
for m in latex_like[:5]:
    print(f"  {m}")
