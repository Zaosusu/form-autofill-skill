#!/usr/bin/env python3
"""Manage the form-autofill-skill fixed-info profile (single source of truth).

Subcommands:
  init              create profile with default empty keys (idempotent)
  show              print the whole profile as JSON
  set <k> <v...>    set a key to a value
  get <k>           print a single key's value
  path              print which profile file is in effect (with a location hint)

档案位置由 scripts/paths.py 解析，默认就是**仓库区**里的 profile.json（.gitignore 隔离，不入库）。
"""
import json
import os
import sys

import paths

# Common keys seeded on first init. Values are filled by the user.
# 姓名拆分为 real_name / stage_name，配合 name_pref 决定"姓名"类字段填哪个。
DEFAULT_KEYS = {
    "real_name": "",   # 真实姓名（证件/法定/实名场景使用）
    "stage_name": "",  # 艺名/化名（默认优先填，除非字段要求真实姓名）
    "name_pref": "real",  # "stage"=优先填艺名；"real"=优先填真名
    "gender": "",      # 性别
    "phone": "",       # 手机号
    "email": "",       # 邮箱
    "wechat": "",      # 微信号
    "org": "",         # 单位/学校
    "title": "",       # 职务/角色
    "major": "",       # 专业/方向
    "city": "",        # 城市
    "address": "",     # 收货地址
    "team_name": "",   # 默认队名（可按赛事覆盖）
    "anonymous": "否", # 匿名提交（否/是）
}


def load():
    p = paths.profile_path()
    if not os.path.exists(p):
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def save(data):
    p = paths.profile_path_for_write()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def cmd_init():
    data = load()
    for k, v in DEFAULT_KEYS.items():
        data.setdefault(k, v)
    save(data)
    print(f"Profile initialized at {paths.profile_path()}")
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_show():
    print(json.dumps(load(), ensure_ascii=False, indent=2))


def cmd_set(key, value):
    data = load()
    data[key] = value
    save(data)
    print(f"set {key} = {value}")


def cmd_get(key):
    print(load().get(key, ""))


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: profile.py [init|show|set <k> <v>|get <k>|path]")
        return
    cmd = args[0]
    if cmd == "init":
        cmd_init()
    elif cmd == "show":
        cmd_show()
    elif cmd == "set":
        if len(args) < 3:
            print("usage: profile.py set <key> <value>")
            return
        cmd_set(args[1], " ".join(args[2:]))
    elif cmd == "get":
        if len(args) < 2:
            print("usage: profile.py get <key>")
            return
        cmd_get(args[1])
    elif cmd == "path":
        print(paths.describe())
    else:
        print(f"unknown command: {cmd}")


if __name__ == "__main__":
    main()
