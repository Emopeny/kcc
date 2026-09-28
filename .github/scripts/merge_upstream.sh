#!/usr/bin/env bash
# 把上游 ciromattia/kcc 合进本 fork，并自动消解「已知会反复冲突」的文件。
#
# 为什么需要它：本 fork 自己改过的文件（README.md、gui/KCC.qrc）一旦和上游改到
# 同几行，裸 `git merge` 必然冲突，定时任务就整条卡死 —— 上游的更新永远合不进来。
# 所以这里把冲突按白名单消解；白名单之外一律硬失败，绝不把坏结果推上去。
#
# 白名单策略：
#   README.md    跟上游（README 归上游维护；本 fork 的中文说明在 .github/KCC-ZH.md）
#                想反过来锁住 fork 版：设 README_POLICY=ours
#   gui/KCC.qrc  以上游版为底，再补回本 fork 的 i18n 资源块（两边的内容都要）
#
# 用法：bash .github/scripts/merge_upstream.sh [upstream-ref]
set -euo pipefail

UPSTREAM_REF=${1:-upstream/master}
README_POLICY=${README_POLICY:-theirs}
SUMMARY=${GITHUB_STEP_SUMMARY:-/dev/stdout}

note() { echo "$1" >> "$SUMMARY"; }

if git merge --no-edit "$UPSTREAM_REF"; then
  echo "上游与 fork 合并干净（无冲突）"
  note "- 合并干净，无需自动消解"
  exit 0
fi

mapfile -t conflicts < <(git diff --name-only --diff-filter=U)
echo "::warning::合并出现冲突：${conflicts[*]}"

resolved=()
unhandled=()

for f in "${conflicts[@]}"; do
  case "$f" in
    README.md)
      if [ "$README_POLICY" = "ours" ]; then
        git checkout --ours -- "$f"
        side="保留 fork 版"
      else
        git checkout --theirs -- "$f"
        side="跟随上游版"
      fi
      git add -- "$f"
      resolved+=("- \`$f\` —— $side")
      ;;

    gui/KCC.qrc)
      # 资源清单是「两边都要」：上游新增的图标 + 本 fork 的 i18n 资源块
      git checkout --theirs -- "$f"
      if grep -q 'prefix="i18n"' "$f"; then
        side="跟随上游版（i18n 资源块已在其中）"
      else
        python - "$f" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
block = (
    '  <qresource prefix="i18n">\n'
    '    <file alias="kcc_zh_CN.qm">../i18n/kcc_zh_CN.qm</file>\n'
    '    <file alias="qtbase_zh_CN.qm">../i18n/qtbase_zh_CN.qm</file>\n'
    '  </qresource>\n'
)
if "</RCC>" not in text:
    sys.exit("KCC.qrc 结构不符合预期：找不到 </RCC>")
path.write_text(text.replace("</RCC>", block + "</RCC>", 1), encoding="utf-8")
print("i18n 资源块已补回 gui/KCC.qrc")
PY
        side="上游版 + 补回 i18n 资源块"
      fi
      git add -- "$f"
      resolved+=("- \`$f\` —— $side")
      ;;

    *)
      unhandled+=("$f")
      ;;
  esac
done

if [ ${#unhandled[@]} -gt 0 ]; then
  note "## ❌ 上游合并遇到需要人工判断的冲突（未推送）"
  note "冲突文件（不在自动消解白名单内）：\`${unhandled[*]}\`"
  {
    echo ""
    echo '```diff'
    for f in "${unhandled[@]}"; do
      echo "===== $f ====="
      git diff -- "$f" | sed -n '1,120p'
    done
    echo '```'
  } >> "$SUMMARY"
  echo "::error::以下冲突不在白名单内，需要人工处理：${unhandled[*]}"
  exit 1
fi

git commit --no-edit
note "## ✅ 上游合并完成（冲突已按白名单自动消解）"
for line in "${resolved[@]}"; do
  note "$line"
done
