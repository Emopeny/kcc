#!/usr/bin/env python3
"""生成一个用于自检的多页测试漫画包(.cbz)。

用途：在 GitHub Actions 里验证 KCC 云端链路是否可用，不依赖任何外部素材。
"""
import os
import zipfile

from PIL import Image, ImageDraw

W, H = 1072, 1448
PAGES = 6
OUT_DIR = os.environ.get("OUT_DIR", "in")
OUT_NAME = os.environ.get("OUT_NAME", "kcc-selftest.cbz")

os.makedirs(OUT_DIR, exist_ok=True)
pages = []
for i in range(1, PAGES + 1):
    img = Image.new("RGB", (W, H), (250, 250, 248) if i % 2 else (245, 245, 240))
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, W - 40, H - 40], outline=(30, 30, 30), width=6)
    d.line([40, H // 2, W - 40, H // 2], fill=(120, 120, 120), width=3)
    d.text((W // 2 - 40, H // 2 - 30), f"PAGE {i}/{PAGES}", fill=(20, 20, 20))
    d.text((80, 90), "KCC CLOUD SELFTEST", fill=(60, 60, 60))
    path = os.path.join(OUT_DIR, f"page{i:03d}.png")
    img.save(path, "PNG")
    pages.append(path)

cbz_path = os.path.join(OUT_DIR, OUT_NAME)
with zipfile.ZipFile(cbz_path, "w", zipfile.ZIP_DEFLATED) as z:
    for p in pages:
        z.write(p, os.path.basename(p))
for p in pages:
    os.remove(p)

print(f"selftest archive: {cbz_path} ({os.path.getsize(cbz_path)} bytes, {PAGES} pages)")
