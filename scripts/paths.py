#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""路径解析 —— 「仓库区即唯一源，私人配置住在 user/」。

技能根目录 = 本文件所在目录的上一级（即含 SKILL.md 的那层）。
私人配置一律放在：<skill_root>/user/
    user/profile.json       固定信息档案
    user/feishu_creds.json  飞书开放平台凭证（可选）
整个 user/ 被 .gitignore 隔离（只保留一个 user/.gitkeep 占位），永不入库。
→ 这就是「用 ignore 隔离私人数据和私人配置」的落点。

档案解析优先级：
  1. 环境变量 FORM_AUTOFILL_PROFILE          —— 显式覆盖，最高优先
  2. <skill_root>/user/profile.json           —— 仓库区（推荐，唯一源）
  3. <skill_root>/profile.json                —— 兼容早期放在技能根的写法
  4. <skill_root>/.profile_root 指向的路径     —— 已安装镜像目录用，见下
  5. ~/.workbuddy/form-autofill-skill/profile.json —— 旧位置，仅向后兼容回退

关于 4：WorkBuddy 只从 ~/.workbuddy/skills/<name>/ 加载技能，那是**加载入口镜像**，
不含私人配置。跑过 scripts/deploy.sh 后镜像里会留一个 .profile_root 文本文件写明
真实仓库根，于是镜像里的脚本也能解析到仓库区那份档案 —— 私人数据全局仍只有一份。
"""
import os

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER_DIR = os.path.join(SKILL_ROOT, "user")
USER_PROFILE = os.path.join(USER_DIR, "profile.json")
ROOT_PROFILE = os.path.join(SKILL_ROOT, "profile.json")   # 兼容旧写法
POINTER_FILE = os.path.join(SKILL_ROOT, ".profile_root")
LEGACY_PROFILE = os.path.join(
    os.path.expanduser("~"), ".workbuddy", "form-autofill-skill", "profile.json"
)


def skill_root() -> str:
    return SKILL_ROOT


def user_dir() -> str:
    """私人配置目录（可能不存在，写入前会创建）。"""
    return USER_DIR


def _candidates(raw: str):
    """把「指针 / 环境变量」的值展开成一串候选档案文件路径。

    值可能是：档案文件本身 | 技能根目录（含 user/）| user/ 目录
    """
    p = os.path.expanduser(raw.strip().strip('"').strip("'"))
    if not p:
        return []
    if os.path.isfile(p):
        return [p]
    if os.path.isdir(p):
        # 技能根：优先 user/profile.json，其次根下 profile.json（兼容旧写法）
        return [os.path.join(p, "user", "profile.json"),
                os.path.join(p, "profile.json")]
    # 路径还不存在（还没 init）：按扩展名猜——目录结尾则补档案名
    if p.endswith(("/", os.sep)):
        return [os.path.join(p, "profile.json")]
    return [p]


def _first_existing(raw: str):
    for c in _candidates(raw):
        if os.path.exists(c):
            return c
    return None


def profile_path() -> str:
    """返回当前生效的档案路径（不保证文件已存在）。"""
    env = os.environ.get("FORM_AUTOFILL_PROFILE", "").strip()
    if env:
        return _first_existing(env) or _candidates(env)[0]
    if os.path.exists(USER_PROFILE):
        return USER_PROFILE
    if os.path.exists(ROOT_PROFILE):
        return ROOT_PROFILE
    if os.path.exists(POINTER_FILE):
        try:
            with open(POINTER_FILE, "r", encoding="utf-8") as f:
                hit = _first_existing(f.read())
            if hit:
                return hit
        except OSError:
            pass
    if os.path.exists(LEGACY_PROFILE):
        return LEGACY_PROFILE
    # 都不存在：默认落在仓库区的 user/ 下（首次 init 时会建目录）
    return USER_PROFILE


def profile_path_for_write() -> str:
    """写入用路径。与 profile_path() 一致，避免"读到 A 却写到 B"的意外迁移。"""
    return profile_path()


def describe() -> str:
    p = profile_path()
    norm = os.path.normcase(os.path.abspath(p))
    if norm == os.path.normcase(os.path.abspath(USER_PROFILE)):
        loc = "仓库区 user/（唯一源，被 .gitignore 隔离）"
    elif norm == os.path.normcase(os.path.abspath(ROOT_PROFILE)):
        loc = "技能根旧写法（建议移到 user/）"
    elif norm == os.path.normcase(os.path.abspath(LEGACY_PROFILE)):
        loc = "旧家目录（已弃用，建议迁到 user/）"
    elif os.path.basename(os.path.dirname(p)) == "user":
        loc = "由 .profile_root 指向的仓库区 user/"
    else:
        loc = "自定义"
    return f"{p}  [{loc}]"
