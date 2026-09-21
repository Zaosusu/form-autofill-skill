# launch_visible_chrome.ps1
# 目的：在【用户自己的 Windows 登录会话】里拉起一个"用户能亲眼看见"的 Chrome，
#       并开好远程调试端口，供 agent-browser 通过 `connect 9222` 驱动。
#
# 为什么不用 agent-browser 的 open：它自起的 Chrome 跑在工作沙箱的隔离显示里，
# 用户的物理屏幕上看不到（窗口是空白/不显示）。用 Windows 计划任务 + Interactive 登录类型
# 拉起，父进程变成 Task Scheduler 服务（svchost），窗口就落到用户的 console 会话（Session 1）。
#
# 用法（管理员/普通用户均可，普通用户即可）：
#   powershell -ExecutionPolicy Bypass -File launch_visible_chrome.ps1 -Url "https://....feishu.cn/share/base/form/XXXX"
# 参数：
#   -Url        要打开的地址（默认 about:blank）
#   -Port       远程调试端口（默认 9222）
#   -ProfileDir 固定 user-data-dir（默认 C:\Users\<你>\.wb_chrome_view\data）——
#               务必固定同一个目录，否则全新配置会每次弹出 Chromium 首次"登录"页。
#   -ChromeExe  Chrome 可执行文件（默认取 agent-browser 自带的那份）
#
# 拉起后：
#   agent-browser connect <Port>
#   agent-browser snapshot -i
#   agent-browser click "@eNN" / fill "@eNN" "..."
#   # 注意：每条 agent-browser 命令前都要重新 connect <Port>（连接不跨命令保留）
# 收尾（关掉可见窗口）：
#   Stop-ScheduledTask -TaskName WBChromeView; Unregister-ScheduledTask -TaskName WBChromeView -Force
#   Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force

param(
  [string]$Url = "about:blank",
  [int]$Port = 9222,
  [string]$ProfileDir = "$env:USERPROFILE\.wb_chrome_view\data",
  [string]$ChromeExe = "$env:USERPROFILE\.agent-browser\browsers\chrome-153.0.8010.36\chrome.exe",
  [string]$TaskName = "WBChromeView"
)

if (-not (Test-Path $ChromeExe)) {
  Write-Error "找不到 Chrome: $ChromeExe（请安装 agent-browser 或改 -ChromeExe 指向系统 Chrome）"
  exit 1
}
New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null

$arg = "--no-sandbox --remote-debugging-port=$Port --user-data-dir=""$ProfileDir"" --window-position=150,100 --window-size=1000,1100 ""$Url"""
$action = New-ScheduledTaskAction -Execute $ChromeExe -Argument $arg
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $action -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName

Start-Sleep -Seconds 5
try {
  $cdp = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/json/version" -UseBasicParsing -TimeoutSec 5
  Write-Output "CDP OK ($Port): $($cdp.StatusCode)"
} catch {
  Write-Output "CDP NOT REACHABLE: $($_.Exception.Message)"
}
$p = Get-Process -Name chrome -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if ($p) { Write-Output "Visible window: PID=$($p.Id) Session=$($p.SessionId) Title='$($p.MainWindowTitle)'" }
else    { Write-Output "No visible chrome window detected" }
