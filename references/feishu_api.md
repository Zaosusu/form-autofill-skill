# 飞书表单：Open API / CLI 提交（可选路径）

当本机已配置飞书开放平台应用凭证时，可用 API 直接写入底表记录，比浏览器填入更稳、不受前端改版/反爬影响。这是「填表」的第二条自动化路径（第一条是浏览器，见 SKILL.md 第 5 步）。

## 适用前提
- 你**拥有或已被授权**该多维表格（Base）。公开分享表单若你不是所有者/协作者，拿不到 `app_token`/`table_id`，此路不通——回退到浏览器填入。
- 已创建飞书开放平台应用，拿到 `app_id` + `app_secret`，并给应用开通「多维表格」读写权限范围（bitable）。

## 步骤
1. 取 `app_token` 与 `table_id`：
   - 在浏览器打开该 Base 编辑页，URL 形如 `https://<domain>.feishu.cn/base/<app_token>?table=<table_id>`。
   - 或用接口列举：`GET https://open.feishu.cn/open-apis/bitable/v1/apps/<app_token>/tables`（需 token）。
2. 拿 `tenant_access_token`：
   `POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal`
   body: `{"app_id":"...","app_secret":"..."}` → 返回 `tenant_access_token`。
3. 写入记录（即「提交表单」）：
   `POST https://open.feishu.cn/open-apis/bitable/v1/apps/<app_token>/tables/<table_id>/records`
   Header: `Authorization: Bearer <tenant_access_token>`
   Body: `{"fields": {"字段名或字段ID": <值>, ...}}`
   - 字段名用 Base 里的列名；单选/多选需传选项文本（须与表里选项完全一致）。
   - 某些表单专属字段（如「匿名提交」）在底表里可能没有对应列，按底表实际列填即可。
4. 返回 `code:0` 即成功。

## 与浏览器路径的关系
- 默认走浏览器（agent-browser）零配置，任何人丢个链接就能填。
- 走 API 需一次性配凭证，但适合高频、批量、或前端改版频繁的场景。
- 无论哪条路，**提交动作仍建议最终由人类确认**（见 SKILL.md 第 6 步）；若要全自动提交，须人类明确授权。

## 注意
- 凭证（`app_secret`）属敏感信息，存到仓库区的私人配置目录 `user/feishu_creds.json`（整目录被 `.gitignore` 的 `user/*` 隔离），不要写进 skill 目录的其它位置、更不要提交到仓库。
- 不同飞书域（feishu.cn / larksuite.com）host 不同，按实际域替换 `open.feishu.cn`。
