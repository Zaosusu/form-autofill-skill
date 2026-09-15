# 字段匹配规则（label → profile key）

`scripts/map_fields.py` 按以下规则把表单字段标签映射到固定信息档案的键。**从上到下顺序匹配，命中即停**（所以更具体的标签要排在前面，例如「队长邮箱」会先命中 `email` 而非其它）。

| profile key | 匹配关键词（标签含其一即命中） | 含义 |
|---|---|---|
| `anonymous` | 匿名 | 匿名提交 |
| `name` | 姓名、名字、真实姓名、name | 姓名 |
| `gender` | 性别、sex、gender | 性别 |
| `phone` | 手机、电话、联系电话、mobile、phone、tel | 手机号/电话 |
| `email` | 邮箱、电子邮件、邮件、email、e-mail、mail | 邮箱 |
| `wechat` | 微信、微信号、wechat、wx | 微信号 |
| `id_number` | 身份证、证件号、证件号码、护照、id number | 证件号（敏感，缺省则问人） |
| `org` | 单位、公司、企业、学校、院校、机构、组织、学院、school、company、org、organization | 单位/学校 |
| `title` | 职务、职位、角色、岗位、头衔、title、role、position | 职务/角色 |
| `major` | 专业、方向、研究领域、学科、major、subject | 专业/方向 |
| `city` | 城市、所在城市、city | 城市 |
| `address` | 收货地址、地址、邮寄地址、联系地址、address | 收货地址 |
| `team_name` | 队名、团队名称、队伍名称、小队名称、组名、team | 队名 |
| `team_size` | 队员人数、队伍人数、团队人数、成员数、人数、members | 队员人数 |
| `project_desc` | 项目简介、项目描述、项目说明、参赛项目、简介、描述、description、intro | 项目简介 |
| `remark` | 备注、备注信息、remark、note、其他 | 备注 |

## 姓名解析（name 字段特殊处理）
档案里 `name` 不存值，而是由 `real_name` + `stage_name` + `name_pref` 解析得出：
- 标签含真实姓名信号（真实姓名 / 实名 / 法定 / 身份证 / 证件 / 法定姓名）→ 强制填 `real_name`。
- 否则按 `name_pref`：
  - `"stage"`（默认）→ 填 `stage_name`；若艺名为空则回退 `real_name`。
  - `"real"` → 填 `real_name`。
- 用户设定示例：`name_pref = "stage"`，即「只要不要求填真名就优先填艺名」。

## 匹配结果判定
- 命中 key 且档案有非空值 → `mode: auto`（直接填）。
- 单选/多选/下拉：档案值需在 `options` 中精确命中才 `auto`；否则 `mode: ask` 并给 `suggestion`（最相近选项）。
- 未命中 key，或命中但档案为空 → `mode: ask`（交人类）。

## 扩展
遇到新的高频字段时，在这里和 `map_fields.py` 的 `PATTERNS` 里同步加一行即可。
