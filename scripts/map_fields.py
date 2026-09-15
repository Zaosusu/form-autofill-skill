#!/usr/bin/env python3
"""Map extracted form fields to the fixed-info profile.

Input : profile.json (path via --profile, else default) + a fields JSON.
        fields JSON = list of {"label", "type", "required", "options"}
        Read from a file path (positional arg) or from stdin.
Output: JSON array, one item per field:
        {"label","type","required","options","profile_key","value","mode","suggestion"}
        mode = "auto"  -> value taken from profile, safe to fill
        mode = "ask"   -> no match / empty profile / option mismatch -> human needed
        suggestion     -> for select fields, a best-guess option to offer the human

Label -> profile_key matching rules mirror references/field_patterns.md.
"""
import json
import os
import sys

PROFILE_DEFAULT_PATH = os.path.join(
    os.path.expanduser("~"), ".workbuddy", "form-autofill-skill", "profile.json"
)

# (profile_key, [keywords]) — first match wins, evaluated top to bottom.
PATTERNS = [
    ("anonymous", ["匿名"]),
    ("name", ["姓名", "名字", "真实姓名", "name"]),
    ("gender", ["性别", "sex", "gender"]),
    ("phone", ["手机", "电话", "联系电话", "mobile", "phone", "tel"]),
    ("email", ["邮箱", "电子邮件", "邮件", "email", "e-mail", "mail"]),
    ("wechat", ["微信", "微信号", "wechat", "wx"]),
    ("id_number", ["身份证", "证件号", "证件号码", "护照", "id number"]),
    ("org", ["单位", "公司", "企业", "学校", "院校", "机构", "组织", "学院",
             "school", "company", "org", "organization"]),
    ("title", ["职务", "职位", "角色", "岗位", "头衔", "title", "role", "position"]),
    ("major", ["专业", "方向", "研究领域", "学科", "major", "subject"]),
    ("city", ["城市", "所在城市", "city"]),
    ("address", ["收货地址", "地址", "邮寄地址", "联系地址", "address"]),
    ("team_name", ["队名", "团队名称", "队伍名称", "小队名称", "组名", "team"]),
    ("team_size", ["队员人数", "队伍人数", "团队人数", "成员数", "人数", "members"]),
    ("project_desc", ["项目简介", "项目描述", "项目说明", "参赛项目",
                      "简介", "描述", "description", "intro"]),
    ("remark", ["备注", "备注信息", "remark", "note", "其他"]),
]

SELECT_TYPES = {"select", "单选", "多选", "下拉", "combobox", "radio",
                "checkbox", "single_select", "multi_select"}

# 标签含以下信号时，"姓名"类字段强制填真实姓名（而非艺名）
REAL_NAME_SIGNALS = ["真实姓名", "实名", "法定", "身份证", "证件", "法定姓名"]


def resolve_name_value(profile, label):
    """决定 name 类字段填真名还是艺名。"""
    l = label or ""
    if any(s in l for s in REAL_NAME_SIGNALS):
        return profile.get("real_name", "")
    pref = profile.get("name_pref", "real")
    if pref == "stage":
        return profile.get("stage_name", "") or profile.get("real_name", "")
    return profile.get("real_name", "")


def match_key(label):
    l = (label or "").lower()
    for key, kws in PATTERNS:
        for kw in kws:
            if kw.lower() in l:
                return key
    return None


def main():
    args = sys.argv[1:]
    profile_path = PROFILE_DEFAULT_PATH
    rest = []
    i = 0
    while i < len(args):
        if args[i] == "--profile":
            profile_path = args[i + 1]
            i += 2
        else:
            rest.append(args[i])
            i += 1

    if rest:
        with open(rest[0], "r", encoding="utf-8") as f:
            fields = json.load(f)
    else:
        fields = json.load(sys.stdin)

    profile = {}
    if os.path.exists(profile_path):
        with open(profile_path, "r", encoding="utf-8") as f:
            profile = json.load(f)

    out = []
    for fld in fields:
        label = fld.get("label", "")
        ftype = (fld.get("type") or "").lower()
        required = bool(fld.get("required", False))
        options = fld.get("options") or []
        key = match_key(label)
        if key == "name":
            value = resolve_name_value(profile, label)
        else:
            value = profile.get(key, "") if key else ""
        mode = "ask"
        suggestion = None

        if key and value not in (None, ""):
            if ftype in SELECT_TYPES and options:
                exact = next((o for o in options if str(o) == str(value)), None)
                if exact is not None:
                    value = exact
                    mode = "auto"
                else:
                    fuzzy = next(
                        (o for o in options
                         if str(value) in str(o) or str(o) in str(value)),
                        None,
                    )
                    suggestion = fuzzy if fuzzy is not None else (options[0] if options else None)
                    mode = "ask"
            else:
                mode = "auto"
        # known key but empty profile value -> ask; unknown key -> ask

        out.append({
            "label": label,
            "type": ftype,
            "required": required,
            "options": options,
            "profile_key": key,
            "value": value,
            "mode": mode,
            "suggestion": suggestion,
        })

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
