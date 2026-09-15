#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# deploy.sh —— 把【仓库区】同步到 WorkBuddy 的【已安装技能目录】（加载镜像）。
#
# 设计原则：
#   仓库区 = 唯一源（代码 + 私人档案 profile.json，档案被 .gitignore 隔离）
#   已安装目录 = 纯镜像，只负责让 WorkBuddy 能加载到 SKILL.md
#
# 行为：
#   * 只【覆盖 / 新增】，从不删除目标里的任何文件（用户硬规矩）。
#   * 不复制 user/ —— 私人配置只留在仓库区。
#   * 在镜像里写一个 .profile_root 指针，写明仓库根，使镜像里的脚本
#     也能解析到仓库区那份档案（数据仍只有一份）。
#
# 用法：
#   bash scripts/deploy.sh                       # 装到 ~/.workbuddy/skills/form-autofill-skill
#   SKILL_INSTALL_DIR=/path/to/dir bash scripts/deploy.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${SKILL_INSTALL_DIR:-$HOME/.workbuddy/skills/form-autofill-skill}"

if [ ! -f "$REPO_ROOT/SKILL.md" ]; then
  echo "✗ 找不到 $REPO_ROOT/SKILL.md —— 这不是技能仓库根" >&2
  exit 1
fi

mkdir -p "$TARGET"
echo "源（仓库区）: $REPO_ROOT"
echo "目标（镜像）: $TARGET"
echo "---"

copied=0
# 逐个文件复制：只覆盖/新增，不删
while IFS= read -r rel; do
  [ -z "$rel" ] && continue
  case "$rel" in
    # 私人配置 / 指针 / git 内部 —— 不进镜像
    user/*|user|profile.json|*/.profile_root|.git/*|*/.git/*) continue ;;
  esac
  src="$REPO_ROOT/$rel"
  dst="$TARGET/$rel"
  mkdir -p "$(dirname "$dst")"
  if [ -f "$dst" ] && cmp -s "$src" "$dst"; then
    continue          # 内容相同，跳过
  fi
  cp -p "$src" "$dst"
  if [ -f "$dst" ]; then echo "  ✓ $rel"; else echo "  ✗ $rel"; fi
  copied=$((copied + 1))
done < <(cd "$REPO_ROOT" && find . -type f \
           -not -path './.git/*' -not -path './user/*' \
           -not -name 'profile.json' \
           -not -name '.profile_root' | sed 's|^\./||' | sort)

# 写指针：让镜像里的 scripts/paths.py 找到仓库区的档案
# 注意：必须写【原生路径】——Git Bash 的 /d/... 形式 Windows Python 解析不了。
if command -v cygpath >/dev/null 2>&1; then
  NATIVE_ROOT="$(cygpath -w "$REPO_ROOT")"
else
  NATIVE_ROOT="$REPO_ROOT"
fi
printf '%s\n' "$NATIVE_ROOT" > "$TARGET/.profile_root"
echo "---"
echo "同步完成：$copied 个文件变更"
echo "档案指针: $TARGET/.profile_root -> $NATIVE_ROOT\\user\\profile.json"
