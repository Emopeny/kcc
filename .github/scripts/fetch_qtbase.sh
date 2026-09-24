#!/usr/bin/env bash
# 获取 Qt 自带的 qtbase 中文翻译目录，供 QMessageBox 的 OK/Yes/No 等标准按钮使用。
#
# 依次尝试：
#   1. PySide6 自带目录（有的版本会带）
#   2. 官方 Qt 翻译仓库 qt/qttranslations：下载 .ts 后用 pyside6-lrelease 编译
#   3. 都拿不到 → 生成空占位文件
#      （rcc 引用该文件，缺了会失败；空文件让 QTranslator.load 返回 False，
#        运行时会优雅降级为英文，不会崩）
set -uo pipefail

OUT="i18n/qtbase_zh_CN.qm"
mkdir -p i18n

QT_TR=$(python -c "import PySide6,os;print(os.path.join(os.path.dirname(PySide6.__file__),'translations'))" 2>/dev/null || true)
echo "PySide6 translations 目录: ${QT_TR:-<未找到>}"

if [ -n "$QT_TR" ] && [ -f "$QT_TR/qtbase_zh_CN.qm" ]; then
  cp "$QT_TR/qtbase_zh_CN.qm" "$OUT"
  echo "=> 取自 PySide6 自带目录"
  ls -l "$OUT"
  exit 0
fi

echo "PySide6 未自带 qtbase_zh_CN.qm；该目录现有内容："
ls "$QT_TR" 2>/dev/null | head -20 || true

for REF in 6.9 6.8 dev; do
  URL="https://raw.githubusercontent.com/qt/qttranslations/$REF/translations/qtbase_zh_CN.ts"
  echo "尝试 $URL"
  if curl -fsSL --retry 2 --retry-delay 3 -o /tmp/qtbase_zh_CN.ts "$URL"; then
    if pyside6-lrelease /tmp/qtbase_zh_CN.ts -qm "$OUT" >/dev/null 2>&1 && [ -s "$OUT" ]; then
      echo "=> 已由官方 .ts 编译得到（分支 $REF）"
      ls -l "$OUT"
      exit 0
    fi
  fi
done

echo "::warning::未能获取 qtbase 中文目录，QMessageBox 标准按钮将保持英文"
: > "$OUT"
ls -l "$OUT"
