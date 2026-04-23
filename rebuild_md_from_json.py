"""Rebuild per-page markdown fragments from saved JSONs."""
import os
import json
from pathlib import Path

WORK_DIR = os.environ.get("WORK_DIR", "/tmp/book-convert")

JSON_DIR = Path(f"{WORK_DIR}/structure_json")
MD_DIR = Path(f"{WORK_DIR}/md_parts")
MD_DIR.mkdir(exist_ok=True)

count = 0
for jf in sorted(JSON_DIR.glob("page-*.json")):
    pnum = int(jf.stem.split("-")[1])
    md_out = MD_DIR / f"page-{pnum:03d}.md"
    if md_out.exists():
        continue
    try:
        data = json.loads(jf.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"skip {jf.name}: {e}")
        continue
    # The PP-StructureV3 JSON has various keys; reading-order text typically
    # lives under `parsing_res_list` or we can pull `overall_ocr_res.rec_texts`.
    text = ""
    try:
        # Preferred: parsing_res_list holds ordered text blocks
        if "parsing_res_list" in data:
            parts = []
            for block in data["parsing_res_list"]:
                if isinstance(block, dict):
                    t = block.get("block_content") or block.get("content") or ""
                    if t:
                        parts.append(t.strip())
            text = "\n\n".join(parts)
        elif "overall_ocr_res" in data:
            rec = data["overall_ocr_res"].get("rec_texts", [])
            text = "\n\n".join(t for t in rec if t.strip())
        else:
            # Fallback: any "rec_texts" anywhere
            def scan(d):
                if isinstance(d, dict):
                    if "rec_texts" in d and isinstance(d["rec_texts"], list):
                        return d["rec_texts"]
                    for v in d.values():
                        r = scan(v)
                        if r:
                            return r
                elif isinstance(d, list):
                    for v in d:
                        r = scan(v)
                        if r:
                            return r
                return None
            rt = scan(data)
            if rt:
                text = "\n\n".join(t for t in rt if t.strip())
    except Exception as e:
        print(f"parse {jf.name}: {e}")

    md_out.write_text(text, encoding="utf-8")
    count += 1

print(f"wrote {count} md fragments from {len(list(JSON_DIR.glob('page-*.json')))} JSONs")
