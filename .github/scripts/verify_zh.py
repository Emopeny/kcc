#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证「中文版 KCC」是否真的中文化。

上游 12.1.x 起自带多语言：源码里的文案全部走 Qt 的 translate() 机制，
翻译表在 translations/kcc_zh_CN.ts，构建时 lrelease 编译成 .qm，
再由 rcc 编进资源系统 :/i18n/kcc_zh_CN.qm。

本 fork 不再自己包运行时替换层，所以这里只验「上游机制 + 本 fork 的译法是否生效」。
断言以语义为主（译文 ≠ 英文原文且含汉字），不锁具体用词，方便跟随上游更新。

用法：
  python .github/scripts/verify_zh.py
      跑源码形态：从 translations/kcc_zh_CN.qm 装载
  python .github/scripts/verify_zh.py --require-resource
      rcc 之后：从资源 :/i18n/kcc_zh_CN.qm 装载（打包后真正走的路径）
  python .github/scripts/verify_zh.py --require-resource --require-default-zh
      打包前：额外断言默认语言是 zh_CN（构建时用 set_zh_default.py 钉住）

任一条不成立即退出码非 0。
"""
import ast
import os
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

require_resource = "--require-resource" in sys.argv
require_default_zh = "--require-default-zh" in sys.argv

TS_FILE = os.path.join(ROOT, "translations", "kcc_zh_CN.ts")
QM_FILE = os.path.join(ROOT, "translations", "kcc_zh_CN.qm")
QRC_FILE = os.path.join(ROOT, "gui", "KCC.qrc")
RES_PATH = ":/i18n/kcc_zh_CN.qm"

# 上游 12.1.5 的翻译表是 280 条；本 fork 再补 2 条。留出余量，低于此数说明 ts 被截断了
MIN_TRANSLATIONS = 250

fails = []


def has_han(s):
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


def check(label, ok, detail=""):
    print(f"{'OK  ' if ok else 'FAIL'} {label}" + (f"\n      实际: {detail}" if detail else ""))
    if not ok:
        fails.append(f"{label}: {detail}")


def check_zh(label, got, src):
    """语义断言：已中文化 = 与原文不同且含汉字。"""
    check(label, got != src and has_han(got), repr(got))


from PySide6.QtCore import QCoreApplication, QFile, QTranslator   # noqa: E402
from PySide6.QtWidgets import QApplication, QMainWindow            # noqa: E402

app = QApplication([sys.argv[0]])

# --- 1) 翻译表本身：齐不齐、有没有漏译 -------------------------------------
total = 0
unfinished = []
if not os.path.exists(TS_FILE):
    check("翻译表存在", False, TS_FILE)
else:
    root = ET.parse(TS_FILE).getroot()
    for ctx in root.findall("context"):
        ctx_name = ctx.findtext("name")
        for msg in ctx.findall("message"):
            total += 1
            translation = msg.find("translation")
            text = (translation.text or "") if translation is not None else ""
            if translation is None or not text.strip() or translation.get("type") == "unfinished":
                unfinished.append(f"{ctx_name}: {(msg.findtext('source') or '')[:50]}")
    check(f"翻译表条数 ≥ {MIN_TRANSLATIONS}", total >= MIN_TRANSLATIONS, f"{total} 条")
    check("翻译表无未翻译条目", not unfinished,
          f"{len(unfinished)} 条: {unfinished[:5]}")

# --- 2) 装载 ----------------------------------------------------------------
if require_resource:
    from kindlecomicconverter import KCC_rc  # noqa: F401  仅为让资源系统注册进来
    res = QFile(RES_PATH)
    check(f"资源 {RES_PATH} 存在", res.exists() and res.size() > 1000,
          f"exists={res.exists()} size={res.size() if res.exists() else 0}")
    load_path = RES_PATH
else:
    check("编译产物 translations/kcc_zh_CN.qm 存在", os.path.exists(QM_FILE), QM_FILE)
    load_path = QM_FILE

translator = QTranslator()
loaded = translator.load(load_path)
check(f"QTranslator.load({load_path!r})", loaded, str(loaded))
if loaded:
    app.installTranslator(translator)

# --- 3) 控件层（KCC_ui.py 生成时埋的 translate()）-------------------------
for ctx, source in [
    ("mainWindow", "Convert"),
    ("mainWindow", "Preserve Margin %"),
    ("mainWindow", "Cropping power:"),
    ("editorDialog", "Cancel"),
]:
    check_zh(f"translate({ctx!r}, {source!r})",
             QCoreApplication.translate(ctx, source), source)

# --- 4) 运行时消息（上游改成 QCoreApplication.translate / self.tr 的那些）---
for source in [
    "Creating EPUB files",
    "Conversion interrupted.",
    "Attempting file fusion",
    "All jobs completed.",
]:
    check_zh(f"translate('KCCGUI', {source!r})",
             QCoreApplication.translate("KCCGUI", source), source)

# --- 5) 真实界面：拿生成的 Ui_mainWindow 建一次窗口，断言控件文字 ----------
from kindlecomicconverter import KCC_ui  # noqa: E402

window = QMainWindow()
ui = KCC_ui.Ui_mainWindow()
ui.setupUi(window)
check_zh("convertButton.text()", ui.convertButton.text(), "Convert")
check_zh("窗口标题", window.windowTitle(), "Kindle Comic Converter")

# --- 6) 资源清单：.qm 必须由 gui/KCC.qrc 打进 :/i18n/ ----------------------
qrc = open(QRC_FILE, encoding="utf-8").read() if os.path.exists(QRC_FILE) else ""
check("gui/KCC.qrc 绑定 translations/kcc_zh_CN.qm",
      'alias="kcc_zh_CN.qm"' in qrc and "../translations/kcc_zh_CN.qm" in qrc,
      "未在 qrc 中找到 i18n 资源条目")

# --- 7) 默认语言（构建时钉成中文）------------------------------------------
if require_default_zh:
    from kindlecomicconverter import i18n as kcc_i18n
    check("i18n.DEFAULT_LANGUAGE == 'zh_CN'",
          kcc_i18n.DEFAULT_LANGUAGE == "zh_CN", repr(kcc_i18n.DEFAULT_LANGUAGE))
    check("apply_language('zh_CN') 生效",
          kcc_i18n.apply_language("zh_CN") == "zh_CN", "apply_language 返回非 zh_CN")

# --- 8) 守卫：设备名 / 格式名是程序逻辑键，绝不能被翻译 --------------------
logic = set()
gui_src = os.path.join(ROOT, "kindlecomicconverter", "KCC_gui.py")
if os.path.exists(gui_src):
    tree = ast.parse(open(gui_src, encoding="utf-8").read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
            for target in node.targets:
                if isinstance(target, ast.Attribute) and target.attr in ("profiles", "formats"):
                    for key in node.value.keys:
                        if isinstance(key, ast.Constant) and isinstance(key.value, str):
                            logic.add(key.value)
if logic and os.path.exists(TS_FILE):
    ts_sources = set()
    for ctx in ET.parse(TS_FILE).getroot().findall("context"):
        for msg in ctx.findall("message"):
            ts_sources.add((msg.findtext("source") or "").strip())
    leaked = sorted(k for k in logic if k in ts_sources)
    check(f"逻辑键守卫（{len(logic)} 个设备/格式名）", not leaked,
          f"被误译: {leaked}")

if fails:
    print("\n==== 中文化验证未通过 ====")
    for item in fails:
        print(" -", item)
    sys.exit(1)

print("\n==== 中文化验证全部通过 ====")
