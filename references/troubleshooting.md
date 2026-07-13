# 故障排查

## 登录文件找不到

- 确认 WorkBuddy 桌面端已经安装并登录。
- 先运行 `scripts/workbuddy_checkin.py --dry-run`。
- Windows 优先检查 `%LOCALAPPDATA%`，再检查 `%APPDATA%`。
- 路径确有变化时设置 `WORKBUDDY_TOKEN_FILE`，只填写路径，不复制 Token 内容。

## 登录凭证失效

退出并重新登录 WorkBuddy，然后再次运行 `--dry-run`。不要把登录文件发给任何人。

## Mac 任务没有运行

检查：

```bash
launchctl print "gui/$(id -u)/io.github.workbuddy-auto-checkin.daily"
tail -n 30 "$HOME/Library/Logs/WorkBuddyAutoCheckin/checkin.log"
```

电脑关机时不会执行；睡眠期间错过的日历任务通常会在唤醒后补跑。

## Windows 任务没有运行

检查：

```cmd
schtasks /Query /TN "WorkBuddyAutoCheckin" /V /FO LIST
type "%LOCALAPPDATA%\WorkBuddyAutoCheckin\logs\checkin.log"
```

任务使用当前登录用户身份。电脑关机时不会执行；任务设置了 `StartWhenAvailable`，错过时间后会尽快补跑。

## 出现重复请求

检查是否同时存在旧的签到脚本、WorkBuddy 内部自动化或其他计划任务。确认后重新安装：

```bash
python3 scripts/install.py --time 06:05 --replace-legacy
```

旧定义会先备份到安装目录的 `legacy-backup`。
