#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 KCC 中文化是否真正生效。

断言方式以「语义」为主：译文必须与英文原文不同且含汉字。
这样调整具体用词不会导致自检误报，适配跟随上游自动重建的场景。

检查项：
  0. （加 --require-resource 时）翻译文件必须已进入 Qt 资源系统
  1. 翻译文件能否装载
  2. 控件层：Qt translate() 是否已中文化
  3. 运行时层：整串 / 片段替换 / 拼接消息 / 控制指令透传
  4. 真实界面：用生成的 Ui_mainWindow 构建窗口，断言控件文字
  5. 原生对话框：文件对话框标题与过滤器、消息框标题
  6. Qt 自带目录：QMessageBox 标准按钮已中文化（qtbase 取不到时只提示）
  7. 守卫：设备名 / 格式名是程序逻辑键，绝不能被翻译

任一条不成立即退出码非 0。
"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

require_resource = "--require-resource" in sys.argv

from PySide6.QtCore import QCoreApplication, QFile        # noqa: E402
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox  # noqa: E402

from kindlecomicconverter.i18n import install_translator, tr_runtime  # noqa: E402

fails = []


def has_han(s):
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


def check(label, got, want):
    ok = got == want
    print(f"{'OK  ' if ok else 'FAIL'} {label}\n      实际: {got!r}")
    if not ok:
        fails.append(f"{label}: 期望 {want!r}, 实际 {got!r}")


def check_zh(label, got, src):
    """语义断言：已中文化 = 与原文不同且含汉字。"""
    ok = got != src and has_han(got)
    print(f"{'OK  ' if ok else 'FAIL'} {label}\n      实际: {got!r}")
    if not ok:
        fails.append(f"{label}: 未中文化（原文 {src!r} → 实际 {got!r}）")


def check_passthrough(label, got, src):
    """控制指令 / 纯数字必须原样透传。"""
    ok = got == src
    print(f"{'OK  ' if ok else 'FAIL'} {label}\n      实际: {got!r}")
    if not ok:
        fails.append(f"{label}: 应原样透传，实际 {got!r}")


app = QApplication([sys.argv[0]])

# --- 0) 打包形态检查 ---
qtbase_size = 1
if require_resource:
    from kindlecomicconverter import KCC_rc  # noqa: F401
    for res in (":/i18n/kcc_zh_CN.qm", ":/i18n/qtbase_zh_CN.qm"):
        f = QFile(res)
        ok, size = f.exists(), (f.size() if f.exists() else 0)
        print(f"{'OK  ' if ok else 'FAIL'} 资源 {res} 存在\n      实际: {ok} ({size} bytes)")
        if not ok:
            fails.append(f"资源缺失: {res}")
    qtbase_size = QFile(":/i18n/qtbase_zh_CN.qm").size()

# --- 1) 装载 ---
check("install_translator()", install_translator(app), True)

# --- 2) 控件层 ---
check_zh('translate("mainWindow", "Convert")',
         QCoreApplication.translate("mainWindow", "Convert"), "Convert")
check_zh('translate("mainWindow", "Preserve Margin %")',
         QCoreApplication.translate("mainWindow", "Preserve Margin %"), "Preserve Margin %")
check_zh('translate("editorDialog", "Cancel")',
         QCoreApplication.translate("editorDialog", "Cancel"), "Cancel")

# --- 3) 运行时层 ---
check_zh("运行时整句", tr_runtime("Creating EPUB files"), "Creating EPUB files")
check_zh("运行时片段替换", tr_runtime("[1/3] Processing images"), "[1/3] Processing images")
check_zh("运行时拼接消息", tr_runtime("Created fusion at /tmp/x.cbz"),
         "Created fusion at /tmp/x.cbz")
check_passthrough("控制指令透传", tr_runtime("tick"), "tick")
check_passthrough("数字透传", tr_runtime("42"), "42")

# --- 5) 原生对话框 ---
check_zh("文件对话框标题", tr_runtime("Select file"), "Select file")
check_zh("文件对话框过滤器", tr_runtime("Comic (*.pdf);;All (*.*)"),
         "Comic (*.pdf);;All (*.*)")
check_zh("消息框标题", tr_runtime("KCC - Error"), "KCC - Error")

# --- 4) 真实界面 ---
from kindlecomicconverter import KCC_ui  # noqa: E402

window = QMainWindow()
ui = KCC_ui.Ui_mainWindow()
ui.setupUi(window)
check_zh("convertButton.text()", ui.convertButton.text(), "Convert")
check_zh("gammaLabel.text()", ui.gammaLabel.text(), "Gamma: Auto")
check_zh("croppingPowerLabel.text()", ui.croppingPowerLabel.text(), "Cropping power:")
check_zh("窗口标题", window.windowTitle(), "Kindle Comic Converter")

# --- 6) Qt 自带目录：消息框标准按钮 ---
box = QMessageBox()
box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
labels = sorted(b.text() for b in box.buttons())
if qtbase_size > 0:
    ok = all(has_han(x) for x in labels)
    print(f"{'OK  ' if ok else 'FAIL'} QMessageBox 标准按钮\n      实际: {labels}")
    if not ok:
        fails.append(f"QMessageBox 标准按钮未中文化: {labels}")
else:
    print(f"SKIP QMessageBox 标准按钮（qtbase 目录未取到，已优雅降级）\n      实际: {labels}")

# --- 7) 守卫：逻辑键不得被翻译 ---
ts = os.path.join(ROOT, "i18n", "kcc_zh_CN.ts")
if os.path.exists(ts):
    tree = ast.parse(open(os.path.join(ROOT, "kindlecomicconverter", "KCC_gui.py"),
                          encoding="utf-8").read())
    logic = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict):
            for t in n.targets:
                if isinstance(t, ast.Attribute) and t.attr in ("profiles", "formats"):
                    for k in n.value.keys:
                        if isinstance(k, ast.Constant) and isinstance(k.value, str):
                            logic.add(k.value)
    src = open(ts, encoding="utf-8").read()
    leaked = [k for k in logic if f"<source>{k}</source>" in src]
    print(f"{'OK  ' if not leaked else 'FAIL'} 逻辑键守卫（{len(logic)} 个设备/格式名）\n"
          f"      被误译: {leaked}")
    if leaked:
        fails.append(f"逻辑键被翻译，会导致功能失效: {leaked}")

if fails:
    print("\n==== 中文化验证未通过 ====")
    for f in fails:
        print(" -", f)
    sys.exit(1)

print("\n==== 中文化验证全部通过 ====")
