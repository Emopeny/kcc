#!/usr/bin/env bash
# 把上游 ciromattia/kcc 合进本 fork，并自动消解「必然卡住流水线」的冲突。
#
# 这里堵的是两层坑：
#
# 1) 上游与本 fork 会改到同一批文件：README.md、gui/KCC.qrc，以及
#    上游从 12.1.x 起自己做的多语言改造（kindlecomicconverter/KCC_gui.py、
#    kindlecomicconverter/i18n.py、translations/*.ts）。裸 `git merge` 必然冲突，
#    每天定时的「跟随上游自动中文化」就会卡死，上游的更新永远合不进来。
#    所以按白名单自动消解：源码一律跟上游（本 fork 不再自己包 i18n 层），
#    只有「中文措辞」这一层是本 fork 的东西，合完再盖回去。
#
# 2) GITHUB_TOKEN 是 GitHub App 令牌，没有 workflows 权限：
#    只要合并结果动了 .github/workflows/**，push 一律被拒
#       refusing to allow a GitHub App to create or update workflow ... without workflows permission
#    （按 ref 判定的，改分支也一样拒。permissions 块里没有 workflows 这个键，加不出来。）
#    处置：推送用带 workflow 权限的令牌（secret SYNC_PUSH_TOKEN），工作流文件照常跟上游。
#    默认 WORKFLOWS_POLICY=ours（保 fork 版）是给「没有该令牌、在本地裸跑」的情形兜底；
#    正式工作流里显式设成 theirs。
#
# 白名单之外的冲突一律硬失败（先 merge --abort 再退出），绝不把坏结果推上去。
#
# 用法：bash .github/scripts/merge_upstream.sh [upstream-ref]
set -euo pipefail

UPSTREAM_REF=${1:-upstream/master}
README_POLICY=${README_POLICY:-theirs}      # theirs=README 跟上游；ours=保 fork 版
WORKFLOWS_POLICY=${WORKFLOWS_POLICY:-ours}  # ours=工作流文件保 fork 版；theirs=跟上游（需 workflow 权限令牌）
SUMMARY=${GITHUB_STEP_SUMMARY:-/dev/stdout}

note() { echo "$1" >> "$SUMMARY"; }

# --no-commit：干净合并与冲突合并都在下面统一处理、统一提交
git merge --no-commit --no-edit "$UPSTREAM_REF" >/dev/null || true

mapfile -t conflicts < <(git diff --name-only --diff-filter=U)
if [ ${#conflicts[@]} -gt 0 ]; then
  echo "::warning::合并出现冲突：${conflicts[*]}"
fi

resolved=()
unhandled=()

for f in "${conflicts[@]:-}"; do
  [ -n "$f" ] || continue
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

    .github/workflows/*)
      # 工作流文件：跟上游（push 令牌必须带 workflow 权限，否则 GitHub 直接拒）
      if [ "$WORKFLOWS_POLICY" = "ours" ]; then
        git checkout --ours -- "$f"
        side="保留 fork 版"
      else
        git checkout --theirs -- "$f"
        side="跟随上游版"
      fi
      git add -- "$f"
      resolved+=("- \`$f\` —— $side")
      ;;

    gui/KCC.qrc|kindlecomicconverter/KCC_gui.py|kindlecomicconverter/i18n.py)
      # 上游自己就是这套 i18n 机制的发源方：源码一律跟上游，本 fork 不再打补丁
      git checkout --theirs -- "$f"
      git add -- "$f"
      resolved+=("- \`$f\` —— 跟随上游版（源码层不再由 fork 改造）")
      ;;

    translations/kcc_zh_CN.ts)
      # 中文翻译表：上游版为底（保住上游新加的串），再盖上本 fork 定过的措辞
      git checkout --theirs -- "$f"
      python3 .github/scripts/apply_zh_overrides.py
      git add -- "$f"
      resolved+=("- \`$f\` —— 上游版 + 本 fork 译法（zh_overrides.json）")
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
  git merge --abort
  echo "::error::以下冲突不在白名单内，需要人工处理：${unhandled[*]}"
  exit 1
fi

# --- 中文翻译表：无条件把本 fork 的措辞盖到上游版之上 -----------------------
# 上游新增翻译表时是「干净新增」，不会进上面的冲突循环，所以这里不能只在冲突分支里处理。
if [ -f translations/kcc_zh_CN.ts ] && [ -f .github/zh_overrides.json ]; then
  python3 .github/scripts/apply_zh_overrides.py
  git add -- translations/kcc_zh_CN.ts
  note "- \`translations/kcc_zh_CN.ts\` —— 上游版 + 本 fork 译法（.github/zh_overrides.json）"
fi

# --- 工作流文件：默认保 fork 版，否则 push 会被 GitHub App 权限规则拒绝 ---
skipped_wf=()
if [ "$WORKFLOWS_POLICY" = "ours" ]; then
  mapfile -t wf < <(git diff --name-only --diff-filter=ACDMR HEAD -- .github/workflows || true)
  for f in "${wf[@]:-}"; do
    [ -n "$f" ] || continue
    if git cat-file -e "HEAD:$f" 2>/dev/null; then
      git checkout HEAD -- "$f"          # 上游改了/删了 → 恢复 fork 版
    else
      git rm -q -f --cached --ignore-unmatch -- "$f" >/dev/null 2>&1 || true
      rm -f -- "$f"                      # 上游新增的 → 不跟进
    fi
    skipped_wf+=("$f")
  done
fi

git commit --no-edit --allow-empty >/dev/null

note "## ✅ 上游合并完成（冲突已按白名单自动消解）"
for line in "${resolved[@]:-}"; do
  [ -n "$line" ] || continue
  note "$line"
done

if [ ${#skipped_wf[@]} -gt 0 ]; then
  note ""
  note "### ⏭ 上游改动的工作流文件未跟进（保 fork 版）"
  for f in "${skipped_wf[@]}"; do
    note "- \`$f\`"
  done
  note ""
  note "原因：GITHUB_TOKEN 没有 workflows 权限，改工作流文件的提交推不上去。"
  note "需要时用带 workflow 权限的令牌手动搬，或把 push 令牌换成 PAT 并设 \`WORKFLOWS_POLICY=theirs\`。"
  echo "::warning::已跳过上游的工作流改动（保 fork 版）：${skipped_wf[*]}"
fi
