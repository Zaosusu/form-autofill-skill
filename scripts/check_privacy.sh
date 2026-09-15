#!/usr/bin/env bash
# check_privacy.sh —— push 前的一键隐私自检（只读，不修改任何文件）。
#
# 检查四件事：
#   1. user/ 下的私人配置是否真的被 .gitignore 拦住
#   2. 【被 git 跟踪】的文件里是否残留敏感串 —— 敏感串从 user/profile.json 现读，
#      本脚本自身【不含任何真实私人数据】，可安全入库
#   3. 通用模式（11 位手机号 / 常见邮箱域）扫描
#   4. git add -A --dry-run 会不会误把私人档案带进暂存区
#
# 用法：
#   bash scripts/check_privacy.sh
#   bash scripts/check_privacy.sh 额外敏感串1 额外敏感串2
#
# 退出码：0 = 通过；1 = 发现问题（不要 push）。
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || exit 1

fail=0
say() { printf '%s\n' "$*"; }
ok()  { printf '  \033[32m✓\033[0m %s\n' "$*"; }
bad() { printf '  \033[31m✗\033[0m %s\n' "$*"; fail=1; }

# ---------------------------------------------------------------- 1) ignore
say "===== 1) .gitignore 是否拦住 user/ 下的私人配置 ====="
for f in user/profile.json user/feishu_creds.json user/any-random-note.txt user/sub/deep.json .profile_root; do
  if git check-ignore -q "$f"; then ok "忽略生效: $f"; else bad "未被忽略（危险）: $f"; fi
done
if git check-ignore -q user/.gitkeep; then
  bad "user/.gitkeep 被判为忽略 —— clone 后 user/ 目录会丢失"
else
  ok "user/.gitkeep 已放行（目录可在 clone 后保留）"
fi

# ------------------------------------------------- 2) 从本机档案现读敏感串
say ""
say "===== 2) 从 user/profile.json 现读敏感串，扫【被跟踪】文件 ====="

PY=""
for c in python python3 py; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done

tokens=()
if [ -n "$PY" ] && [ -f user/profile.json ]; then
  while IFS= read -r line; do
    [ -n "$line" ] && tokens+=("$line")
  done < <("$PY" - <<'PYEOF' 2>/dev/null || true
import json
# 这些键是配置项而非隐私（值形如 real/stage/否），跳过以免误报
SKIP_KEYS = {"name_pref", "anonymous"}
try:
    d = json.load(open("user/profile.json", encoding="utf-8"))
except Exception:
    raise SystemExit
for k, v in d.items():
    if k in SKIP_KEYS or not isinstance(v, str):
        continue
    s = v.strip()
    if not s:
        continue
    ascii_only = all(ord(ch) < 128 for ch in s)
    # 纯 ASCII 太短的（如 4 字符的缩写）容易误报，要求 >=6；含中文的 >=2 即保留
    if (ascii_only and len(s) >= 6) or (not ascii_only and len(s) >= 2):
        print(s)
PYEOF
)
  if [ "${#tokens[@]}" -gt 0 ]; then
    ok "从本机档案读到 ${#tokens[@]} 个敏感串（值不回显，只报命中数）"
  else
    say "  (档案为空或读不到，仅做通用模式扫描)"
  fi
else
  say "  (未找到 python 或 user/profile.json，跳过档案取值)"
fi

# 追加命令行传入的自定义串
for t in "$@"; do [ -n "$t" ] && tokens+=("$t"); done

if [ "${#tokens[@]}" -eq 0 ]; then
  say "  (无敏感串可扫)"
else
  for tok in "${tokens[@]}"; do
    hits=$(git grep -I -l -- "$tok" 2>/dev/null | tr '\n' ' ')
    if [ -z "$hits" ]; then ok "命中 0 处"; else bad "命中：$hits"; fi
  done
fi

# ------------------------------------------------------- 3) 通用模式
say ""
say "===== 3) 通用模式扫描 ====="
hits=$(git grep -I -l -E -- '\b1[3-9][0-9]{9}\b' 2>/dev/null || true)
if [ -z "$hits" ]; then ok "11 位手机号 -> 0 命中"; else bad "疑似手机号：$hits"; fi

hits=$(git grep -I -n -E -- '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.(com|cn|net|org)' 2>/dev/null \
       | grep -viE 'example\.(com|org)|noreply|@qq\.com/|you@' || true)
if [ -z "$hits" ]; then
  ok "邮箱模式 -> 0 命中"
else
  bad "疑似真实邮箱："; printf '%s\n' "$hits" | sed 's/^/      /'
fi

# ------------------------------------------------------- 4) 暂存区
say ""
say "===== 4) git add -A --dry-run 会不会带上私人档案 ====="
dry=$(git add -A --dry-run 2>&1 || true)
if printf '%s' "$dry" | grep -qE 'profile\.json|feishu_creds\.json|\.profile_root'; then
  bad "暂存区会包含私人文件："
  printf '%s\n' "$dry" | grep -E 'profile\.json|feishu_creds\.json|\.profile_root' | sed 's/^/      /'
else
  ok "暂存区不含 profile.json / feishu_creds.json / .profile_root"
fi

# ------------------------------------------------------- 汇总
say ""
say "===== 汇总 ====="
say "跟踪文件数: $(git ls-files | wc -l | tr -d ' ')"
if [ "$fail" = "0" ]; then
  printf '结果：\033[32m全部通过\033[0m —— 可以 push。\n'
  exit 0
else
  printf '结果：\033[31m发现问题\033[0m —— 先修好再 push。\n'
  exit 1
fi
