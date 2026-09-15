---
name: form-autofill-skill
description: This skill should be used when the user wants to fill out an online form (especially 飞书/Feishu 多维表格公开表单, hackathon/event registration, device or application forms) with their repeated personal or team info. It stores a fixed-info profile, auto-fills fields that map to it, surfaces unknown or context-specific fields for the human to answer, and always requires human confirmation before submitting. Trigger phrases include "填表", "帮我填", "自动填", "这个表单", pasting a form URL, or complaints about repeatedly hand-filling the same details.
---

# Form Autofill（填表助手）

## Purpose
Stop hand-filling the same personal/team details into every hackathon, event, or application form. Keep one fixed-info profile as the single source of truth; auto-fill whatever maps to it; ask the human only for genuinely new or context-specific fields; then present a review sheet and let the human submit.

## Hard Rules
- **Never auto-submit.** Always present the filled result and wait for explicit human confirmation before any "提交"/"提交申请" click.
- **Never guess sensitive data** (passwords, ID numbers, bank info). If absent from the profile, ask the human.
- **Unknown fields → human.** Only auto-fill when a field clearly maps to a profile key with a non-empty value.
- **Prefer asking over wrong guessing** for ambiguous or context-dependent fields (e.g. 项目简介, 队名).
- **Remember answers.** When the human supplies a value for a new field, offer to store it back into the profile so it becomes `auto` next time.

## Privacy & repository layout（隐私与目录结构）
本仓库**只包含 skill 逻辑，不含任何私人信息**。架构上把"skill 本体"与"用户私人数据"彻底分离：

- **私人信息（姓名/手机/邮箱/地址…）**：运行时由 `scripts/profile.py init` 生成在用户家目录
  `~/.workbuddy/form-autofill-skill/profile.json`，**永远在仓库之外**，重装 skill 也不会被清掉。
- **`.gitignore`** 已屏蔽 `profile.json`、`*.local.json`、`feishu_creds.json`，即便在仓库内生成也不会被提交。
- **`examples/profile.example.json`**：脱敏的空模板，仅展示字段 schema，供克隆后照抄填写。
- 飞书应用凭证（`app_id`/`app_secret`）同样存到家目录 `feishu_creds.json` 并被 gitignore，不进仓库。

```
form-autofill-skill/
├── SKILL.md                 # skill 定义（本文件，无私人数据）
├── scripts/
│   ├── profile.py           # 档案管理，默认读写 ~/.workbuddy/form-autofill-skill/profile.json
│   └── map_fields.py        # 字段→档案匹配
├── references/
│   ├── field_patterns.md    # 匹配规则
│   └── feishu_api.md        # 飞书 Open API/CLI 提交（可选）
├── examples/
│   └── profile.example.json # 脱敏模板
└── .gitignore               # 屏蔽所有私人信息
```

## Workflow

### 0. First-time setup (profile)
If the profile does not exist yet, run:
```
python scripts/profile.py init
```
Then collect the user's fixed info (name, gender, phone, email, wechat, org, title, major, city, address, team_name, …) — either by asking, or by having them edit the profile file directly:
```
python scripts/profile.py path      # prints the profile.json location
python scripts/profile.py set <key> <value>
python scripts/profile.py show
```
The profile lives at `~/.workbuddy/form-autofill-skill/profile.json` (private, outside the skill dir so reinstalls don't wipe it).

### 1. Receive a form
Accept a form URL (or pasted field list / screenshot). This skill targets 飞书多维表格公开表单 (`*.feishu.cn/share/base/form/...`) and similar web forms.

### 2. Extract fields
Goal: a JSON list of `{label, type, required, options}`.
- **Preferred:** load the **agent-browser** skill, open the URL, and read every field's label, input type, whether required, and option list (for 单选/多选/下拉).
- **Fallback 1:** `WebFetch` the URL and extract the field list (works for server-rendered forms; SPAs may need the browser).
- **Fallback 2:** if automated extraction fails, ask the human to paste the field labels (or a screenshot) and build the list manually.
Write the result to a temporary `fields.json`.

### 3. Map to profile
Run:
```
python scripts/map_fields.py --profile <profile.json> fields.json
```
(or pipe the fields JSON via stdin). Using the rules in `references/field_patterns.md`, the script outputs, per field:
- `mode: "auto"` — value taken from profile; fill it directly.
- `mode: "ask"` — no profile match or empty; surface to the human. `suggestion` may hint a fuzzy option match.

### 4. Collect the unknowns
For every `mode: "ask"` field, gather the value from the human:
- Use AskUserQuestion for a small set of distinct choices, or ask inline for free text.
- If the field is a 单选/多选/下拉, present its `options` (plus `suggestion` when present).
- After the human answers, **offer to store the answer** into the profile under an appropriate key (so it becomes `auto` next time).

### 5. Fill the form
Load **agent-browser** and set each field's value:
- `auto` fields → type/select the profile value.
- human-provided fields → type/select the human's answer.
- Leave 提交 / 提交申请 untouched.
Keep the browser open at the confirmation step.

### 6. Confirm (mandatory)
Print a review table: `field | value | ✓auto / ✎human`. Explicitly tell the human to review and click 提交 themselves. Do not click submit on their behalf.

## Notes
- **飞书/办公类表单允许自动化。** 浏览器自动化与飞书 Open API/CLI 两条路都可用——「禁用浏览器自动化」是 mcn-studio 针对微信抓取的封号风险规矩，仅限小红书、抖音、微信等内容/社交平台，**不适用于飞书这类办公表单**（用户 2026-09-15 明确）。本 skill 默认用浏览器（agent-browser）零配置填入；若提供飞书应用凭证，可改用更稳的 API/CLI 提交（见 `references/feishu_api.md`）。
- `references/field_patterns.md` lists the label→profile-key matching rules; extend it when you meet a new recurring field.
- 飞书表单通常是公开分享链接，填写无需登录。若表单要求登录，先请人类登录，再继续。
- 如果人类更想要「只给答案表、自己复制粘贴」的保守版，跳过第 5 步，直接把对照表交给人类。
