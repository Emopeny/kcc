#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 KCC 中文化是否真正生效。

四层检查，任一条不成立即退出码非 0：
  1. .qm 翻译文件能否装载
  2. 控件层：Qt translate() 是否返回中文
  3. 运行时层：查表与片段替换是否正确（含控制指令必须原样透传）
  4. 真实界面：用生成的 Ui_mainWindow 构建窗口，断言控件文字
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication              # noqa: E402
from PySide6.QtWidgets import QApplication, QMainWindow  # noqa: E402

from kindlecomicconverter.i18n import install_translator, tr_runtime  # noqa: E402

fails = []


def check(label, got, want):
    ok = got == want
    print(f"{'OK  ' if ok else 'FAIL'} {label}\n      实际: {got!r}")
    if not ok:
        fails.append(f"{label}: 期望 {want!r}, 实际 {got!r}")


app = QApplication(sys.argv)

# --- 1) 翻译文件装载 ---
check("install_translator()", install_translator(app), True)

# --- 2) 控件层（Qt 机制） ---
check('translate("mainWindow", "Convert")',
      QCoreApplication.translate("mainWindow", "Convert"), "开始转换")
check('translate("editorDialog", "Cancel")',
      QCoreApplication.translate("editorDialog", "Cancel"), "取消")

# --- 3) 运行时层（查表 + 片段替换） ---
check("tr_runtime 整句", tr_runtime("Creating EPUB files"), "正在生成 EPUB 文件")
check("tr_runtime 片段替换", tr_runtime("[1/3] Processing images"), "[1/3] 正在处理图片")
check("tr_runtime 拼接消息", tr_runtime("Created fusion at /tmp/x.cbz"), "已生成合并文件：/tmp/x.cbz")
check("tr_runtime 控制指令透传", tr_runtime("tick"), "tick")
check("tr_runtime 数字透传", tr_runtime("42"), "42")

# --- 4) 真实界面：用生成的 UI 代码构建窗口 ---
from kindlecomicconverter import KCC_ui  # noqa: E402

window = QMainWindow()
ui = KCC_ui.Ui_mainWindow()
ui.setupUi(window)
check("convertButton.text()", ui.convertButton.text(), "开始转换")
check("gammaLabel.text()", ui.gammaLabel.text(), "伽马：自动")
check("croppingPowerLabel.text()", ui.croppingPowerLabel.text(), "裁边强度：")
check("窗口标题", window.windowTitle(), "Kindle 漫画转换器")

if fails:
    print("\n==== 中文化验证未通过 ====")
    for f in fails:
        print(" -", f)
    sys.exit(1)

print("\n==== 中文化验证全部通过 ====")
