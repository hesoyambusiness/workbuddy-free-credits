# WorkBuddy Auto Check-in

一个无遥测、零第三方 Python 依赖的 WorkBuddy 每日自动签到分享包。每位用户只使用自己电脑上已有的 WorkBuddy 登录状态；工具不收集、不上传、不保存账号凭证。

## 最简单的使用方式

把整个文件夹或 GitHub 仓库链接交给 AI，然后说：

```text
请先阅读 SKILL.md，帮我在这台电脑安装 WorkBuddy 每日自动签到。
每天 06:05 执行；先检查重复任务，安装后立即验证，不要显示或复制我的 Token。
```

AI 会识别 macOS 或 Windows，检查登录状态，安装一套定时任务并验证结果。

## 双击安装

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

- 仓库不包含姓名、微信、邮箱、账号、Token、Cookie 或个人绝对路径。
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
