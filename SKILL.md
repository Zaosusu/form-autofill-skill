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

## Layout & single source of truth

**仓库区就是这个技能的唯一实体。** 代码与私人配置都在仓库里，私人部分集中在 `user/`、由 `.gitignore` 隔离。

```
<repo root>/                     ← 技能根（= SKILL.md 所在层）
├── README.md                    项目说明（给人看：定位/结构/快速开始/隔离/FAQ）
├── SKILL.md                     技能定义（WorkBuddy 加载入口）
├── .gitignore                   隔离 user/ 私人配置 与其它敏感项
├── user/                        ★ 私人配置目录 · 整目录被 ignore，永不入库
│   ├── .gitkeep                 唯一被跟踪的文件（占位，保证目录存在）
│   ├── profile.json             固定信息档案（ignore）
│   └── feishu_creds.json        飞书凭证，可选（ignore）
├── scripts/
│   ├── paths.py                 统一解析「技能根」与「档案路径」
│   ├── profile.py               档案读写（init / show / set / get / path）
│   ├── map_fields.py            表单字段 → 档案键 映射
│   ├── fill_plan.py             快照 + 档案 → agent-browser 命令
│   ├── fill.sh                  填表流程备忘（含全部已知坑）
│   ├── launch_visible_chrome.ps1 让用户「看得见」的浏览器（Windows）
│   ├── check_privacy.sh         push 前的一键隐私自检（只读）
│   └── deploy.sh                仓库区 → 已安装技能目录（加载镜像）
└── references/ examples/        匹配规则 / 示例档案
```

> 面向人的项目说明见 `README.md`；push 前跑一次 `bash scripts/check_privacy.sh`。

- **私人配置一律放 `user/`**（不是技能根、也不是家目录）。当前 `user/` 里是 `profile.json`；
  凭证类（如 `feishu_creds.json`）也放这里 —— 整个目录被 `.gitignore` 的 `user/*` 拦住，**永不入库**。
- **档案解析优先级**（`scripts/paths.py`）：
  1. 环境变量 `FORM_AUTOFILL_PROFILE`（显式覆盖）
  2. `<技能根>/user/profile.json` ← **默认，仓库区**
  3. `<技能根>/profile.json`（兼容早期写法）
  4. `<技能根>/.profile_root` 里写的路径（已安装镜像目录用）
  5. `~/.workbuddy/form-autofill-skill/profile.json`（旧位置，仅向后兼容回退）
  用 `python scripts/profile.py path` 随时查看当前生效的是哪一份。
- **已安装目录只是镜像**：WorkBuddy 只从 `~/.workbuddy/skills/<name>/` 加载技能，那是**加载入口**、不是数据区。改代码请在**仓库区**改，再 `bash scripts/deploy.sh` 同步过去（只覆盖/新增，**从不删除**目标文件，且**不会**复制 `user/`）；deploy 会在镜像里留一个 `.profile_root` 指针，让镜像里的脚本也能找到仓库区那份档案 —— **私人数据全局只有一份**。
- **绝不要在仓库区之外再建一份档案**：数据一分叉就必然漂移。

## Workflow

### 0. First-time setup (profile)
If the profile does not exist yet, run:
```
python scripts/profile.py init
```
Then collect the user's fixed info (name, gender, phone, email, wechat, org, title, major, city, address, team_name, …) — either by asking, or by having them edit the profile file directly:
```
python scripts/profile.py path      # prints which profile.json is in effect
python scripts/profile.py set <key> <value>
python scripts/profile.py show
```
The profile lives at `<技能根>/user/profile.json` —— 就在仓库区里的 `user/`，被 `.gitignore` 隔离，永不入库。参考模板见 `examples/profile.example.json`。

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

### 5b. 让用户"亲眼看见"填表（重要 · Windows）
默认 `agent-browser open` 自起的浏览器跑在**沙箱隔离显示**里 —— 用户的物理屏幕上**看不到**（窗口空白）。如果用户要求"屏幕上/右侧看到你到底填了什么"（本 skill 的常见诉求），必须换路子：
1. 用 `scripts/launch_visible_chrome.ps1`（Windows 计划任务 + `-LogonType Interactive`）在**用户自己的登录会话**里拉起 Chrome，并开 `--remote-debugging-port=9222`。**固定同一个 `--user-data-dir`**，否则全新配置每次都会弹 Chromium 首次"登录 Chromium"页（用户会很烦）。
2. 之后所有操作走 `agent-browser connect 9222` 驱动那个**可见窗口**。关键：**每一条 agent-browser 命令前都要重新 `connect <port>`**（连接状态不跨 shell 调用保留；漏了它会尝试自起浏览器并在沙箱里 exit code 3 崩掉）。
3. 验证落点：`Get-Process chrome | ? {$_.MainWindowHandle -ne 0}` 的 `SessionId` 应等于用户 console 会话（通常 1）；此时 `agent-browser screenshot` 截出来的图**是有内容的**，可自检。
4. 飞书自定义单选/多选：必须用 **`agent-browser click "@<ref>"` 真实鼠标点击**（ref = 快照里"选项文字带引号"那一行）。**JS eval 的 `.click()` 会被 React 还原**，不要用。
5. 收尾：`Stop-ScheduledTask`+`Unregister-ScheduledTask` 名为 `WBChromeView` 的任务并结束 chrome 进程；**提交按钮始终留给用户本人点**。

### 6. Confirm (mandatory)
Print a review table: `field | value | ✓auto / ✎human`. Explicitly tell the human to review and click 提交 themselves. Do not click submit on their behalf.

## Notes
- **飞书/办公类表单允许自动化。** 浏览器自动化与飞书 Open API/CLI 两条路都可用——「禁用浏览器自动化」是 mcn-studio 针对微信抓取的封号风险规矩，仅限小红书、抖音、微信等内容/社交平台，**不适用于飞书这类办公表单**（用户 2026-09-15 明确）。本 skill 默认用浏览器（agent-browser）零配置填入；若提供飞书应用凭证，可改用更稳的 API/CLI 提交（见 `references/feishu_api.md`）。
- **飞书选项选择（易错）**：单选/多选是自定义 `div`、页面无 `<input>`。必须 `agent-browser click "@ref"`（真实鼠标）→ 判定 `...-option-checked`。JS 合成 `click()` 会被 React 还原（2026-09-15 实测结论，纠正了早期"必须用 JS 点容器"的错误说法）。
- **agent-browser 连接不跨命令保留**：驱动外部浏览器时每条命令都要先 `connect <port>`。
- **ref 不跨 bash 调用保留（同源易错）**：`snapshot -i` 得到的 `@ref` 只在**同一条 shell 命令**内有效；换到下一条命令再用就 `✗ Unknown ref`。所以 `snapshot -i` 必须与随后的 `fill/click @ref` 写进**同一条 bash 命令**里（snapshot 落文件 → grep 出 ref → 再 fill/click），不能拆成两次工具调用。
- **其它 open 坑**：`agent-browser open` **绝不能接管道**（如 `| tail`），否则常驻 daemon 占住管道永久卡死；SPA 表单 `open` 后先 `sleep 3~5` 再快照；飞书表单偶发「无法访问此网站」，重开一次即可。
- **可见性**：用户看不到沙箱自起的浏览器；要"用户可见"就用 `scripts/launch_visible_chrome.ps1`（见 5b）。
- `references/field_patterns.md` lists the label→profile-key matching rules; extend it when you meet a new recurring field.
- 飞书表单通常是公开分享链接，填写无需登录。若表单要求登录，先请人类登录，再继续。
- 如果人类更想要「只给答案表、自己复制粘贴」的保守版，跳过第 5 步，直接把对照表交给人类。
