# -*- coding: utf-8 -*-
"""KCC 中文化运行时支持。

KCC 的界面文字分两层：
  * 控件层（按钮/标签/菜单/提示）由 Qt 的 .ts/.qm 机制处理 —— 见 i18n/kcc_zh_CN.ts
  * 运行时消息（任务列表、对话框、托盘通知、进度条）硬编码在源码里，
    统一在消息 funnel 处查本模块的表替换

本文件由工具生成，请勿手改；改翻译请改 i18n/kcc_zh_CN.ts 或重新生成。
"""

import os
import sys

from PySide6.QtCore import QCoreApplication, QTranslator

# 运行时消息表：原文 -> 中文。整句与拼接片段混排，替换时长串优先。
RUNTIME_ZH = {
    'Kindle Comic Converter': 'Kindle 漫画转换器',
    'Kindle Comic Converter ': 'Kindle 漫画转换器 ',
    '<b>Conversion interrupted.</b>': '<b>转换已中断。</b>',
    'Conversion interrupted.': '转换已中断。',
    'Attempting file fusion': '正在尝试文件合并',
    'Created fusion at ': '已生成合并文件：',
    'Fusion Failed. ': '合并失败。',
    'Source:</b> ': '源文件：</b> ',
    'Creating CBZ files': '正在生成 CBZ 文件',
    'Creating folders': '正在创建文件夹',
    'Creating PDF files': '正在生成 PDF 文件',
    'Creating EPUB files': '正在生成 EPUB 文件',
    'Creating MOBI files': '正在生成 MOBI 文件',
    'Processing MOBI files': '正在处理 MOBI 文件',
    'Creating CBZ files... <b>Done!</b>': '正在生成 CBZ 文件... <b>完成！</b>',
    'Creating folders... <b>Done!</b>': '正在创建文件夹... <b>完成！</b>',
    'Creating PDF files... <b>Done!</b>': '正在生成 PDF 文件... <b>完成！</b>',
    'Creating EPUB files... <b>Done!</b>': '正在生成 EPUB 文件... <b>完成！</b>',
    'Creating MOBI files... <b>Done!</b>': '正在生成 MOBI 文件... <b>完成！</b>',
    'Processing MOBI files... <b>Done!</b>': '正在处理 MOBI 文件... <b>完成！</b>',
    'Kindle detected. Uploading covers... <b>Done!</b>': '检测到 Kindle，正在上传封面... <b>完成！</b>',
    '<b>All jobs completed.</b>': '<b>全部任务已完成。</b>',
    'All jobs completed.': '全部任务已完成。',
    'Processing images': '正在处理图片',
    'Compressing CBZ files': '正在压缩 CBZ 文件',
    'Compressing EPUB files': '正在压缩 EPUB 文件',
    'Preparing source images...': '正在准备源图片...',
    'Checking images...': '正在检查图片...',
    'Failed to process MOBI file!': 'MOBI 文件处理失败！',
    'KindleGen failed to create MOBI!': 'KindleGen 生成 MOBI 失败！',
    'KindleGen error:\n\n': 'KindleGen 错误：\n\n',
    'Error during conversion %s:\n\n%s\n\nTraceback:\n%s': '转换出错 %s：\n\n%s\n\n调用栈：\n%s',
    'Error during conversion! Please consult <a href="https://github.com/ciromattia/kcc/wiki/Error-messages">wiki</a> for more details.': '转换出错！详见 <a href="https://github.com/ciromattia/kcc/wiki/Error-messages">wiki</a>。',
    'Error during conversion!': '转换出错！',
    'Created EPUB file was too big. Weird file structure?': '生成的 EPUB 文件过大。文件结构异常？',
    'EPUB file: ': 'EPUB 文件：',
    'MB. Supported size: ~350MB.': 'MB。支持的大小约 350MB。',
    'Your <a href="https://www.amazon.com/b?node=23496309011">KindleGen</a> is outdated! MOBI conversion might fail.': '你的 <a href="https://www.amazon.com/b?node=23496309011">KindleGen</a> 版本过旧！MOBI 转换可能失败。',
    'Source files are probably created by KCC. The second conversion will decrease quality.': '源文件可能已由 KCC 处理过。二次转换会降低画质。',
    'More than 25% of images are smaller than target device resolution.': '超过 25% 的图片小于目标设备分辨率。',
    'Consider enabling stretching or upscaling to improve readability.': '建议启用拉伸或放大以改善可读性。',
    'PDF input can also use legacy extract option if you have any problems': 'PDF 输入如有问题，也可以改用旧版提取选项',
    '"><b>The new version is available!</b></a>': '"><b>有新版本可用！</b></a>',
    'Convert': '开始转换',
    'Abort': '中止',
    'Gamma: Auto': '伽马：自动',
    'Gamma: ': '伽马：',
    'Cropping Power: ': '裁边强度：',
    'CBR files in selection are read-only.': '所选内容中的 CBR 文件为只读。',
    'Editing ': '正在编辑 ',
    ' files.': ' 个文件。',
    'Processing ': '正在处理 ',
    'Errors occurred.': '发生错误。',
    'Successfully updated ': '已成功更新 ',
    ' field must be a number.': ' 字段必须是数字。',
    'Separate authors with a comma.': '多个作者请用逗号分隔。',
    'No changes to apply.': '没有需要应用的更改。',
    '(multiple values)': '（多个值）',
    '(multiple files)': '（多个文件）',
    'e.g., 5 or 1-10 or 1,3,5': '例如 5 或 1-10 或 1,3,5',
}

_FRAGMENTS = sorted(RUNTIME_ZH.items(), key=lambda kv: -len(kv[0]))

_translator = None


def install_translator(app=None):
    """装载 .qm 并安装到 QApplication。必须在构建主窗口之前调用。

    优先从 Qt 资源系统读取（打包后的 exe 走这条），
    其次回退到源码树中的 i18n/kcc_zh_CN.qm（直接跑源码时用）。
    """
    global _translator
    if _translator is not None:
        return True

    candidates = [":/i18n/kcc_zh_CN.qm"]
    here = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(os.path.dirname(here), "i18n", "kcc_zh_CN.qm"))
    if getattr(sys, "_MEIPASS", None):
        candidates.append(os.path.join(sys._MEIPASS, "i18n", "kcc_zh_CN.qm"))

    for path in candidates:
        tr = QTranslator()
        if tr.load(path):
            if app is None:
                app = QCoreApplication.instance()
            if app is not None:
                app.installTranslator(tr)
            _translator = tr
            return True
    return False


def tr_runtime(text):
    """翻译一条运行时消息。命中则返回中文，未命中原样返回。"""
    if not text:
        return text
    hit = RUNTIME_ZH.get(text)
    if hit is not None:
        return hit
    out = text
    for src, zh in _FRAGMENTS:
        if src in out:
            out = out.replace(src, zh)
    return out
