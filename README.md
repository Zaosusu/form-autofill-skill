# form-autofill-skill · 填表助手

> 一次录档，表单自动填；**提交永远由你本人点。**

Stop hand-filling the same name / phone / email / 队名 into every hackathon, event or application form.
Keep **one** fixed-info profile as the single source of truth, auto-fill whatever maps to it,
ask the human only for genuinely new fields — and **never** click submit.

`Python` · `Bash` · `PowerShell` · `agent-browser (CDP)`

---

## 这是什么

一个 **Agent Skill**：给它一个在线表单（默认面向**飞书多维表格公开表单**，也适用于一般 Web 表单），它会

1. 抓出表单里每个字段的标签 / 类型 / 是否必填 / 选项列表；
2. 拿你的**固定信息档案**做映射，能对上的直接填；
3. 对不上的（新字段、创作类内容、敏感信息）**回头问你**；
4. 给你一张对照表复核；
5. 把填好的表单**留在浏览器里等你本人点提交**。

它不保存你的密码，不替你猜身份证号，也不会替你按下「提交」。
解决的问题只有一个：**同一份个人信息，不要每次都手打一遍。**

---

## 设计原则（硬规则）

| 规则 | 含义 |
|---|---|
| **永不自动提交** | 填完停在提交前，必须由人显式确认。`提交` / `提交申请` 一律不碰。 |
| **不猜敏感信息** | 密码、证件号、银行信息 —— 档案里没有就**问人**，绝不推断。 |
| **未知字段交还给人** | 只有「标签明确映射到档案键 + 档案里该键非空」才自动填。 |
| **宁可问，不可填错** | 语义模糊或依赖上下文的字段（项目简介、队名…）宁可问。 |
| **记住答案** | 人回答过的新字段，回写进档案，下次就变成「自动」。 |

---

## 仓库结构

```
<repo root>/                        ← 技能根（= SKILL.md 所在层）
├── README.md                       本文件
├── SKILL.md                        技能定义（Agent 加载入口 + 工作流）
├── .gitignore                      隔离 user/ 私人配置 与其它敏感项
├── user/                           ★ 私人配置目录 · 整目录 ignore，永不入库
│   ├── .gitkeep                    唯一被跟踪的文件（占位，保证目录存在）
│   ├── profile.json                固定信息档案（ignore）
│   └── feishu_creds.json           飞书凭证，可选（ignore）
├── scripts/
│   ├── paths.py                    统一解析「技能根」与「档案路径」
│   ├── profile.py                  档案读写（init / show / set / get / path）
│   ├── map_fields.py               表单字段 → 档案键 映射
│   ├── fill_plan.py                快照 + 档案 → agent-browser 命令
│   ├── fill.sh                     填表流程脚本（含全部已知坑的备忘）
│   ├── launch_visible_chrome.ps1   让用户「看得见」的浏览器（Windows）
│   ├── check_privacy.sh            push 前的一键隐私自检
│   └── deploy.sh                   仓库区 → 已安装技能目录（加载镜像）
├── references/
│   ├── field_patterns.md           标签 → 档案键 匹配规则表
│   └── feishu_api.md               飞书 Open API / CLI 备选路线
└── examples/
    └── profile.example.json        档案模板（空值，占位）
```

---

## 快速开始

### 前置依赖

| 依赖 | 用途 | 说明 |
|---|---|---|
| Python 3.8+ | 跑 `scripts/*.py` | 只用标准库，无第三方包 |
| Node.js | 运行 `agent-browser` | 抓字段 / 填表 |
| [agent-browser](https://github.com/vercel-labs/agent-browser) | 浏览器自动化（CDP） | 也可换成任意 CDP 驱动 |

> 若你只想拿「对照表」自己复制粘贴，可以完全跳过浏览器，只用 Python 部分。

### 1. 建档案（一次性）

```bash
python scripts/profile.py init          # 生成带默认空键的档案（幂等）
python scripts/profile.py set email   you@example.com
python scripts/profile.py set team_name "某某队"
python scripts/profile.py show          # 看全量
python scripts/profile.py path          # 看当前生效的是哪一份档案
```

档案落在 **`<技能根>/user/profile.json`**，被 `.gitignore` 隔离，永不入库。
模板见 `examples/profile.example.json`。

### 2. 抓字段 → 映射 → 补问

```bash
# fields.json: [{"label","type","required","options"}]
python scripts/map_fields.py fields.json
```

每个字段输出 `mode`：

- `mode: "auto"` —— 值来自档案，直接填；
- `mode: "ask"`  —— 未匹配 / 档案为空 / 选项对不上 → **去问人**，`suggestion` 给一个模糊匹配建议。

### 3. 填表（可选，浏览器路线）

```bash
bash scripts/fill.sh <form_url> <spec.json> [out.png]
```

或手动串：

```bash
agent-browser open "<form_url>"        # ⚠️ 绝不能接管道
agent-browser snapshot -i              # 抓 @ref
# snapshot 与随后的 click/fill @ref 必须写在同一条 shell 命令里
```

### 4. 人工提交

对照表复核 → **你本人**点「提交」。本 skill 到此为止。

---

## 亮点：让用户「亲眼看见」填表（Windows）

默认 `agent-browser open` 自起的浏览器跑在**沙箱隔离显示**里 —— 用户物理屏幕上**看不到**（窗口空白）。
如果用户要求「我能看见你到底填了什么」，走这条路：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/launch_visible_chrome.ps1 `
  -Url "https://xxx.feishu.cn/share/base/form/XXXX"
```

原理：**Windows 计划任务 + `-LogonType Interactive`** 拉起 Chrome，父进程变成 Task Scheduler 服务（svchost），
窗口就落到用户自己的 console 会话（通常 `SessionId=1`），同时开 `--remote-debugging-port=9222`
供 `agent-browser connect 9222` 驱动。

收尾：

```powershell
Stop-ScheduledTask -TaskName WBChromeView
Unregister-ScheduledTask -TaskName WBChromeView -Force
Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force
```

**务必固定同一个 `-ProfileDir`**，否则每次全新配置都会弹出 Chromium 首次「登录」页 —— 用户会很烦。

---

## 踩过的坑（都是实测结论）

| 坑 | 结论 |
|---|---|
| 用户看不到自起的浏览器 | 沙箱隔离显示。改用 Windows 计划任务在用户会话里拉，见上。 |
| 飞书单选/多选点了没反应 | 选项是**自定义 `div`**、页面无 `<input>`。必须 `agent-browser click "@ref"`（**真实鼠标**）；JS `element.click()` 会瞬时改 class 但**被 React 还原**。判定：class 含 `...-option-checked` 即选中。 |
| `Unknown ref` | `snapshot -i` 拿到的 `@ref` **只在同一条 shell 命令内有效**。必须把 `snapshot` 与随后的 `fill/click` 写进**同一条命令**。 |
| 命令永久卡死 | `agent-browser open` **绝不能接管道**（`\| tail` 等），常驻 daemon 会占住管道。 |
| 驱动外部浏览器时崩掉 | **连接状态不跨 shell 调用保留** —— 每条命令前都要重新 `connect <port>`，否则它会尝试自起浏览器（沙箱内 `exit code 3`）。 |
| SPA 表单抓不到字段 | `open` 后先 `sleep 3~5` 再 `snapshot`。飞书表单偶发「无法访问此网站」，重开一次即可。 |
| Chrome 直接退出 | 首次自起需 `--args "--no-sandbox"`（exit code 3）。 |

---

## 私人数据隔离

**核心约定：`user/` 就是私人配置的唯一落点，整目录被 `.gitignore` 拦住。**

`.gitignore` 关键部分：

```gitignore
user/*
!user/.gitkeep      # 只放行占位文件，保证 clone 后目录存在
profile.json        # 兜底：万一有档案被误放到技能根
*.local.json
.profile_root       # 已安装镜像里的指针（写明本机仓库路径）
feishu_creds.json
```

### 档案解析优先级（`scripts/paths.py`）

1. 环境变量 `FORM_AUTOFILL_PROFILE` —— 显式覆盖
2. `<技能根>/user/profile.json` —— **默认，仓库区**
3. `<技能根>/profile.json` —— 兼容早期写法
4. `<技能根>/.profile_root` 里写的路径 —— 已安装**镜像**目录用
5. `~/.workbuddy/form-autofill-skill/profile.json` —— 旧位置，仅向后兼容回退

```bash
python scripts/profile.py path   # 随时看当前生效的是哪一份
```

### 一键自检

```bash
bash scripts/check_privacy.sh
```

会检查：`user/` 下私人文件是否被 ignore、**被跟踪文件**里是否残留手机号/邮箱/微信/真名/地址、
以及 `git add --dry-run` 会不会误带上私人档案。

**红线：私人档案与凭证只存在于本机 `user/`，任何情况下不入库、不外发。**

---

## 部署与二次开发

WorkBuddy 只从 `~/.workbuddy/skills/<name>/` 加载技能 —— 那是**加载入口镜像**，不是数据区。

```bash
bash scripts/deploy.sh                 # 仓库区 → 已安装镜像
SKILL_INSTALL_DIR=/path bash scripts/deploy.sh   # 自定义目标
```

`deploy.sh` 的行为：

- 只**覆盖 / 新增**，**从不删除**目标里的任何文件；
- **不复制 `user/`** —— 私人配置只留在仓库区；
- 在镜像里写 `.profile_root`（**原生 Windows 路径**，用 `cygpath -w` 转换），
  让镜像里的脚本也能解析到仓库区那份档案 —— **私人数据全局只有一份**。

> 改代码请改**仓库区**，然后 `bash scripts/deploy.sh` 同步过去。
> 绝不要在仓库区之外再建一份档案 —— 数据一分叉就必然漂移。

---

## FAQ

**Q：会替我点「提交」吗？**
不会。填完就停，提交永远由你本人点。

**Q：飞书表单允许用浏览器自动化吗？**
允许。这里是**办公类表单**，不在「禁用浏览器自动化」的范围内（该限制针对小红书 / 抖音 / 微信等内容平台）。

**Q：能用飞书 Open API 走更稳的路线吗？**
可以，见 `references/feishu_api.md`。需要自建应用凭证，凭证放 `user/feishu_creds.json`（同样被 ignore）。

**Q：换成别的表单（问卷星 / Google Forms / 自建站）能用吗？**
映射层和档案层是通用的；只需喂给它 `{label, type, required, options}` 就能工作，
浏览器驱动部分按目标站点微调即可。

**Q：档案会不会被 push 上去？**
不会。`user/*` 整目录被 ignore，`check_privacy.sh` 可一键复核。

---

## 目录约定

| 目录 | 是什么 | 入库？ |
|---|---|---|
| `SKILL.md` / `scripts/` / `references/` / `examples/` | 技能本体（代码与文档） | ✅ 入库 |
| `user/` | 私人配置（档案、凭证） | ❌ 整目录 ignore，仅 `.gitkeep` 入库 |
| `~/.workbuddy/skills/form-autofill-skill/` | 加载镜像（由 `deploy.sh` 生成） | — 不进 git |

---

## English summary

An **Agent Skill** that auto-fills repeated online forms from a single fixed-info profile.

- Extract fields → map to a profile → auto-fill the matches → **ask the human** for the rest → leave submission to the human.
- **Never auto-submits.** Never guesses sensitive data.
- Private config lives in `user/`, fully git-ignored; a 5-level path resolver keeps **one single source of truth** across the repo and the installed skill mirror.
- Targets 飞书/Feishu public forms; works with generic web forms too, driven by `agent-browser` over CDP.
- Includes a Windows recipe to launch a **user-visible** Chrome window (scheduled task + remote debugging port) so the human can watch the form being filled in real time.

---

## License

尚未指定。若计划开源使用，请补充 `LICENSE` 文件。
