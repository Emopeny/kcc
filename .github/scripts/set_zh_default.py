#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把内置默认语言钉成简体中文（构建期补丁）。

上游 i18n 的默认语言是英文，靠界面上的语言菜单切换（QSettings 记忆用户选择）。
本 fork 出的是「中文版」，所以打包前把 i18n.DEFAULT_LANGUAGE 改成 zh_CN ——
用户第一次打开就是中文，仍可在菜单里换回英文。

只在 CI 的工作树里改，不提交：源码树保持与上游一致，合并上游永远不会为这几行冲突。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TARGET = os.path.join(ROOT, "kindlecomicconverter", "i18n.py")
PATTERN = re.compile(r"^DEFAULT_LANGUAGE\s*=\s*(['\"])(?P<value>\w+)\1", re.MULTILINE)

if not os.path.exists(TARGET):
    sys.exit(f"找不到 {TARGET}")

text = open(TARGET, encoding="utf-8").read()
match = PATTERN.search(text)
if match is None:
    sys.exit(f"{TARGET} 里没有 DEFAULT_LANGUAGE 定义 —— 上游可能改了 i18n 结构，需要人工跟进")

if match.group("value") == "zh_CN":
    print("默认语言已是 zh_CN，无需改动")
    sys.exit(0)

new_text = PATTERN.sub('DEFAULT_LANGUAGE = \'zh_CN\'', text, count=1)
open(TARGET, "w", encoding="utf-8").write(new_text)
print(f"默认语言：{match.group('value')} -> zh_CN")
