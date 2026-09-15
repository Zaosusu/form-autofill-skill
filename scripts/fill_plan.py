#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读飞书表单快照 + 私人档案，输出可直接 bash 执行的 agent-browser 命令。
（本脚本自己不调用 agent-browser —— 避免 python subprocess 卡死。）
用法: python fill_plan.py <snapshot.txt> <spec_json>
spec_json:
  {"text":{"<字段子串>":"<profile键>"},"options":["选项文字(按点击顺序)"]}
profile 键: phone email wechat org title major city address name
文本: agent-browser click @ref + type @ref val
选项: agent-browser click @ref（CDP 真实鼠标。飞书选项是自定义 div，JS 合成 click 会被 React 还原，故不用 eval）
注意: 输出命令依赖快照里的 @ref —— 必须与「取快照」在【同一条 shell 命令】内执行，否则 ref 失效（Unknown ref）。
"""
import sys, re, json, os

PROFILE = os.environ.get("FORM_AUTOFILL_PROFILE",
                         os.path.expanduser("~/.workbuddy/form-autofill-skill/profile.json"))


def main():
    snap = open(sys.argv[1], encoding="utf-8").read()
    spec = json.loads(sys.argv[2])
    profile = json.load(open(PROFILE, encoding="utf-8"))
    name_pref = profile.get("name_pref", "real")
    disp = profile.get("stage_name") if (name_pref == "stage" and profile.get("stage_name")) else profile.get("name", "")
    fv = {
        "phone": profile.get("phone", ""), "email": profile.get("email", ""),
        "wechat": profile.get("wechat", ""), "org": profile.get("org", ""),
        "title": profile.get("title", ""), "major": profile.get("major", ""),
        "city": profile.get("city", ""), "address": profile.get("address", ""),
        "name": disp, "team_name": profile.get("team_name", ""),
        "id_number": profile.get("id_number", ""), "team_size": profile.get("team_size", ""),
        "project_desc": profile.get("project_desc", ""), "remark": profile.get("remark", ""),
    }
    lines = snap.splitlines()
    ref_text = {}
    for ln in lines:
        m = re.search(r"\[ref=(e\d+)\]", ln)
        if not m:
            continue
        q = re.search(r'"([^"]*)"', ln)
        ref_text[m.group(1)] = q.group(1) if q else ""
    inputs = {}
    for i, ln in enumerate(lines):
        if "contenteditable" in ln:
            m = re.search(r"\[ref=(e\d+)\]", ln)
            if not m:
                continue
            iref = m.group(1)
            label = ""
            for j in range(i - 1, -1, -1):
                mm = re.search(r"\[ref=(e\d+)\]", lines[j])
                if mm and ref_text.get(mm.group(1)):
                    label = ref_text[mm.group(1)]
                    break
            inputs[iref] = label

    cmds = []
    for needle, key in spec.get("text", {}).items():
        val = fv.get(key, key)
        matched = next((r for r, lb in inputs.items() if needle in lb), None)
        if matched:
            cmds.append(f'agent-browser click "@{matched}"')
            cmds.append(f'agent-browser type "@{matched}" "{val}"')
            print(f"# 填 [{matched}] {needle} => {val}", file=sys.stderr)
        else:
            print(f"# 缺字段: {needle}", file=sys.stderr)

    opts = spec.get("options", [])
    for opt in opts:
        pat = '"' + opt + '"'
        found = None
        for ln in lines:
            if pat in ln:
                m = re.search(r"\[ref=(e\d+)\]", ln)
                if m:
                    found = m.group(1)
                    break
        if found:
            cmds.append(f'agent-browser click "@{found}"')
            print(f"# 选[{found}] {opt}", file=sys.stderr)
        else:
            print(f"# 选项未找到: {opt}", file=sys.stderr)

    port = os.environ.get("AB_CONNECT_PORT", "").strip()
    if port:
        cmds = [f'agent-browser connect {port} >/dev/null 2>&1; {c}' for c in cmds]
    print("\n".join(cmds))


if __name__ == "__main__":
    main()
