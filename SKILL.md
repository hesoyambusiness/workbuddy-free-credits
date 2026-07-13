---
name: workbuddy-auto-checkin
description: Install, verify, repair, configure, or uninstall one daily WorkBuddy check-in task on macOS or Windows. Use when a user gives an AI this folder or repository and asks to set up WorkBuddy automatic daily credit check-in, change its time, diagnose duplicate check-in jobs, test token discovery without exposing credentials, or remove the automation.
---

# WorkBuddy Auto Check-in

Operate only on the current user's computer and account. Never display, copy, upload, or persist an access token outside WorkBuddy's own auth file.

## Install

1. Detect the operating system.
2. Confirm WorkBuddy is installed and logged in.
3. Choose the requested daily time; use `06:05` when the user gives no time.
4. Run a credential-path check without making a request:

```bash
python3 scripts/workbuddy_checkin.py --dry-run
```

On Windows, use `py -3` instead of `python3` when available.

5. Inspect for existing jobs before installation:
   - macOS: labels containing `workbuddy` and `checkin` or `signin` in `~/Library/LaunchAgents` and `launchctl list`.
   - Windows: scheduled tasks named `WorkBuddyAutoCheckin`, `WorkBuddyCheckin`, or similar.
6. Install one managed job:

```bash
python3 scripts/install.py --time 06:05 --run-now
```

If confirmed duplicate legacy jobs exist, add `--replace-legacy`. The installer backs up their definitions before disabling or deleting them.

7. Verify the managed job and inspect its latest log. A successful claim, `今天已签到`, and `请求处理中，请勿重复操作` are successful idempotent outcomes. Authentication failures and unknown HTTP errors are failures.

## Change time

Run the installer again with the new time. It replaces only this package's managed job:

```bash
python3 scripts/install.py --time HH:MM
```

## Uninstall

```bash
python3 scripts/install.py --uninstall
```

This removes the managed schedule and installed script. It does not delete WorkBuddy credentials. Legacy backups remain available for manual recovery.

## Safety rules

- Never use `cat`, PowerShell `Get-Content`, logging, screenshots, or chat output to expose the auth file.
- Never commit `workbuddy-desktop.info`, logs, tokens, cookies, or user-specific absolute paths.
- Never create more than one managed daily task.
- Do not add retries that can create repeated claims; the service already handles idempotency.
- Do not claim Windows is live-account verified unless a logged-in Windows machine completed a real check-in.
- Read [references/troubleshooting.md](references/troubleshooting.md) only when installation or verification fails.
