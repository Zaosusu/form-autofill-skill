#!/usr/bin/env bash
# 飞书公开表单自动填入（仅填，绝不提交）。需先安装 agent-browser 且 node 可用。
# 用法: bash fill.sh <form_url> <spec.json> [out.png]
#
# ⚠️ 关键坑（务必遵守）：
#  1. agent-browser open 命令【绝不能】接管道（如 | tail），否则常驻 daemon 会占住管道导致永久卡死。
#  2. 连接状态【不跨 shell 调用保留】。驱动外部已启动的 Chrome（connect <port>）时，
#     【每一条】agent-browser 命令前都必须先 `agent-browser connect <port>`，
#     否则它会尝试自己另起浏览器（沙箱内会 exit code 3 崩掉）。
#  3. 要"让用户在自己屏幕上看见填表过程"，不要用 open 自起浏览器——那样 Chrome 跑在沙箱里、用户看不到。
#     正确做法：用 Windows 计划任务（Interactive 登录 + --remote-debugging-port=9222）在用户会话里
#     拉起 Chrome，再用 `agent-browser connect 9222` 驱动它。见 scripts/launch_visible_chrome.ps1。
#  4. 首次自起必须加 --args "--no-sandbox"，否则 Chrome 直接退出（exit code 3）。
#  5. 操作前要先 snapshot -i 注册 ref，否则 click/type @ref 会报 "Unknown ref"。
#     connect 驱动外部浏览器时，每次 connect 后 ref 可能失效，需重新 snapshot；snapshot 前 sleep 2 更稳。
#  6. 飞书单选/多选是自定义 div（页面无 <input>）。必须用【真实鼠标点击】`agent-browser click @<ref>`：
#     快照里"选项文字带引号"那一行的 ref。JS eval 的 element.click() 会瞬时改 class 但被 React 还原，
#     【不要】用 JS 合成点击。判定：选项 class 含 `...-option-checked` 即选中（未选为 `...-option-no-checked`）。
#  7. 重复调用 open 可能新开标签页导致状态读串；尽量复用现有标签，并从新 snapshot 取 ref。
set -u
URL="$1"; SPEC_FILE="$2"; OUT="${3:-filled.png}"
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${PWD}"

agent-browser open "$URL" --args "--no-sandbox"     # 无管道！
sleep 3
agent-browser snapshot -i > _snap.txt 2>&1
python "$DIR/fill_plan.py" _snap.txt "$(cat "$SPEC_FILE")" > _cmds.txt 2>_plan.err
cat _plan.err
bash _cmds.txt
sleep 1
agent-browser screenshot --full "$OUT" > /dev/null 2>&1
agent-browser close > /dev/null 2>&1
echo "screenshot -> $OUT"
