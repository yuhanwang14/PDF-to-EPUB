"""Deep audit: scan for suspicious OCR patterns that indicate content issues."""
import os
import re
from pathlib import Path

TEXT_DIR = Path(f"{WORK_DIR}/epub-extract/EPUB/text")

def extract_text(xhtml):
    # Drop tags, keep text
    txt = re.sub(r"<[^>]+>", "", xhtml)
    # Unescape minimal HTML entities
    txt = (txt.replace("&amp;", "&")
              .replace("&lt;", "<").replace("&gt;", ">")
              .replace("&quot;", '"').replace("&#39;", "'"))
    return txt

all_files = sorted(TEXT_DIR.glob("ch*.xhtml"))

print("=" * 60)
print("A. SUSPICIOUS CHAR PATTERNS (likely OCR errors)")
print("=" * 60)
patterns = [
    ("mid-word Latin (z)", r"[一-鿿]z[一-鿿]"),
    ("mid-word numeric", r"[一-鿿][0-9]{1,2}[一-鿿]"),
    ("stray $", r"\$"),
    ("orphan { or }", r"(?<![$\\])[{}](?![^{}]{0,20}[{}])"),
    ("weird ( ) after nothing", r"\s\)"),
    ("short single-char paragraphs (OCR leftover)", r"<p>.</p>"),
    ("two spaces inside Chinese (rare)", r"[一-鿿]  [一-鿿]"),
    ("'人' at start of word (should be '入')", r"[了到来]人(?=大学|学|门|校|部|住|伍)"),
    ("'入' where should be '人' (人们)", r"入们"),
    ("common OCR mistake '己' vs '已'", r"不己|早己"),
]
for desc, pat in patterns:
    hits = 0
    samples = []
    for f in all_files:
        text = extract_text(f.read_text(encoding="utf-8"))
        for m in re.finditer(pat, text):
            hits += 1
            if len(samples) < 3:
                s, e = m.span()
                samples.append(f"{f.stem}: ...{text[max(0,s-15):e+15]}...")
    print(f"  {desc}: {hits}")
    for s in samples:
        print(f"    {s}")

print("\n" + "=" * 60)
print("B. PARAGRAPH BOUNDARY HEALTH")
print("=" * 60)
broken_count = 0
ends_mid_sentence = 0
total_paragraphs = 0
for f in all_files[1:]:  # skip title page
    text = f.read_text(encoding="utf-8")
    paras = re.findall(r"<p>([^<]+)</p>", text)
    for p in paras:
        total_paragraphs += 1
        if p and p[-1] not in "。！？？!.\"'」』）)》]：:…-—":
            ends_mid_sentence += 1
print(f"Total paragraphs (ex title): {total_paragraphs}")
print(f"Ends mid-sentence (no terminator): {ends_mid_sentence} ({ends_mid_sentence*100//total_paragraphs}%)")

print("\n" + "=" * 60)
print("C. SERVER vs MOBILE OCR TRANSITION (around page 266)")
print("=" * 60)
# Sample sentences from ch026 which is chapter 25, 后记, 译者后记
# Compare: pages 245-266 were server OCR, pages 267-294 were mobile
# Paragraphs that get joined nicely = server; paragraphs broken = mobile
for chap in ["ch026.xhtml", "ch027.xhtml", "ch028.xhtml"]:
    f = TEXT_DIR / chap
    if not f.exists():
        continue
    text = f.read_text(encoding="utf-8")
    paras = re.findall(r"<p>([^<]+)</p>", text)
    avg_len = sum(len(p) for p in paras) / max(len(paras), 1)
    print(f"{chap}: {len(paras)} paragraphs, avg length {avg_len:.0f} chars")

print("\n" + "=" * 60)
print("D. DUPLICATE CONTENT CHECK")
print("=" * 60)
# Check if any paragraph appears twice (indicates duplication)
all_paras = []
for f in all_files:
    text = f.read_text(encoding="utf-8")
    paras = re.findall(r"<p>([^<]+)</p>", text)
    for p in paras:
        if len(p) > 50:
            all_paras.append((f.stem, p[:60]))
from collections import Counter

WORK_DIR = os.environ.get("WORK_DIR", "/tmp/book-convert")
counts = Counter(p for _, p in all_paras)
dupes = [(p, c) for p, c in counts.items() if c > 1]
print(f"Duplicate paragraph openings (>1 occurrence): {len(dupes)}")
for p, c in dupes[:5]:
    print(f"  {c}x: {p}")
