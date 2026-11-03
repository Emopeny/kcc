#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把本 fork 定过的中文措辞盖到上游 translations/kcc_zh_CN.ts 上。

上游 12.1.x 自带 i18n：源码里文案走 Qt translate()，翻译表是
translations/kcc_zh_CN.ts（上游维护，会持续加串）。本 fork 只维护「中文怎么翻」，
所以：
  * 以上游版 .ts 为底 —— 上游新加的串不会丢
  * 同一 (context, source) 用 translations/zh_overrides.json 里的译法覆盖
  * 上游 .ts 漏收的串（lupdate 落后于源码时常见）补进去，避免运行时回落英文

由 merge_upstream.sh 在合并上游后调用；也可以手动跑。幂等。
"""
import json
import os
import sys

# Windows 运行器默认 cp1252，中文 print 会 UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TS_FILE = os.path.join(ROOT, "translations", "kcc_zh_CN.ts")
OVERRIDES_FILE = os.path.join(ROOT, ".github", "zh_overrides.json")


def main():
    if not os.path.exists(TS_FILE):
        sys.exit(f"找不到 {TS_FILE}")
    if not os.path.exists(OVERRIDES_FILE):
        sys.exit(f"找不到 {OVERRIDES_FILE}")

    with open(OVERRIDES_FILE, encoding="utf-8") as f:
        overrides = json.load(f)

    tree = ET.parse(TS_FILE)
    root = tree.getroot()
    contexts = {c.findtext("name"): c for c in root.findall("context")}

    applied = 0
    added = 0
    missing = []

    for ctx_name, entries in overrides.items():
        ctx = contexts.get(ctx_name)
        if ctx is None:
            missing.extend(f"{ctx_name}: {s[:50]}" for s in entries)
            continue
        existing = {}
        for msg in ctx.findall("message"):
            existing[(msg.findtext("source") or "").strip()] = msg

        for source, translation in entries.items():
            source = source.strip()
            msg = existing.get(source)
            if msg is None:
                msg = ET.SubElement(ctx, "message")
                src = ET.SubElement(msg, "source")
                src.text = source
                tr = ET.SubElement(msg, "translation")
                tr.text = translation
                added += 1
                continue
            tr = msg.find("translation")
            if tr is None:
                tr = ET.SubElement(msg, "translation")
            tr.text = translation
            tr.attrib.pop("type", None)
            applied += 1

    raw = ET.tostring(root, encoding="unicode")
    with open(TS_FILE, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n' + raw + "\n")

    print(f"译法覆盖 {applied} 条，补入上游漏收 {added} 条")
    if missing:
        print(f"::warning::有 {len(missing)} 条措辞没匹配上（上游可能改写了原文）：{missing[:5]}")


if __name__ == "__main__":
    main()
