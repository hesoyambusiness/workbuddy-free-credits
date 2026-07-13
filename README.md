# WorkBuddy 全自动免费领积分

免费开源、免费分享，每天自动领取自己 WorkBuddy 账号的签到积分。每位用户只操作自己电脑上当前登录的账号；工具不收集、不上传、不保存账号凭证。

## 安装方法：复制下面这段话发给 WorkBuddy

分享给别人时，只需要发送根目录里的 `安装说明-复制给WorkBuddy.txt`，不需要把整个源码文件夹交给对方。使用者打开安装说明，完整复制下面这段话给 WorkBuddy 即可：

```text
请访问并下载这个公开、免费的开源项目：
https://github.com/liubinne/workbuddy-free-credits

请先完整阅读仓库中的 README.md 和 SKILL.md，再在我当前这台电脑上安装“WorkBuddy 全自动免费领积分”。只操作我当前登录的 WorkBuddy 账号，默认每天 06:05 自动领取积分。请先执行 dry-run，检查并备份旧签到任务，再安装并立即验证。不要在聊天、命令输出或日志中显示、复制、上传我的 Token、Cookie 或登录文件内容。

如果当前无法访问或下载 GitHub，请明确告诉我，不要猜测代码，也不要让我手工复制 Token。
```

WorkBuddy 会自动识别 macOS 或 Windows，下载仓库、检查登录状态、安装定时任务并验证结果。

## 备用方法：双击安装

- macOS：双击 `install-macos.command`。
- Windows：双击 `install-windows.cmd`。

默认每天 `06:05` 运行。需要其他时间时，让 AI 执行：

```bash
python3 scripts/install.py --time 08:30 --run-now
```

Windows 可用 `py -3` 替换 `python3`。

## 安装前提

- 已安装并登录 WorkBuddy 桌面端。
- 已安装 Python 3。
- 电脑在计划时间开机或之后再次唤醒。

## 隐私

- 除本文末尾主动公开的作者名和微信号外，仓库不包含邮箱、账号、Token、Cookie、个人绝对路径或其他个人信息。
- Token 只在签到进程内存中短暂使用，不写入本工具目录和日志。
- 日志只记录时间和脱敏后的成功/失败结果。
- 不要向任何人发送 `workbuddy-desktop.info`。

## 卸载

```bash
python3 scripts/install.py --uninstall
```

卸载不会删除 WorkBuddy 登录信息。日志和旧任务备份会保留，便于排查或恢复。

## 当前验证范围

- macOS：核心请求、登录文件探测、LaunchAgent 生成、安装与卸载流程均可验证。
- Windows：支持 `%LOCALAPPDATA%` 与 `%APPDATA%` 候选路径；计划任务使用完整 Python 路径、支持带空格路径、错过后补跑并保存日志。
- 真实 Windows 账号领取仍应在已登录 WorkBuddy 的 Windows 10/11 电脑上完成最终验收。

## 说明

这是非官方社区工具，与腾讯云、WorkBuddy 或 CodeBuddy 没有隶属、合作或背书关系。接口、登录文件位置和活动规则可能随产品更新而变化，使用者自行决定是否使用并承担账号与服务规则风险。

## License

MIT。详见 `LICENSE`。

作者：鹿游｜微信号：Agent2603
