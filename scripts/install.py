#!/usr/bin/env python3
"""Install or remove one WorkBuddy Auto Check-in scheduled job."""

from __future__ import annotations

import argparse
import getpass
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Optional

LABEL = "io.github.workbuddy-auto-checkin.daily"
WINDOWS_TASK = "WorkBuddyAutoCheckin"
LEGACY_WINDOWS_TASKS = ("WorkBuddyCheckin", "WorkBuddy每日签到")
SCRIPT_NAME = "workbuddy_checkin.py"


def configure_utf8_console() -> None:
    """Keep Chinese status output safe on legacy Windows console encodings."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass


def parse_time(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", value.strip())
    if not match:
        raise argparse.ArgumentTypeError("时间必须是 HH:MM，例如 06:05")
    return int(match.group(1)), int(match.group(2))


def detect_platform(forced: str = "auto") -> str:
    if forced != "auto":
        return forced
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith("win"):
        return "windows"
    raise RuntimeError("目前只支持 macOS 和 Windows")


def ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        path.chmod(0o700)
    except OSError:
        pass


def mac_paths(home: Path) -> dict[str, Path]:
    install_dir = home / "Library" / "Application Support" / "WorkBuddyAutoCheckin"
    return {
        "install_dir": install_dir,
        "script": install_dir / SCRIPT_NAME,
        "log_dir": home / "Library" / "Logs" / "WorkBuddyAutoCheckin",
        "log": home / "Library" / "Logs" / "WorkBuddyAutoCheckin" / "checkin.log",
        "plist": home / "Library" / "LaunchAgents" / f"{LABEL}.plist",
        "backup": install_dir / "legacy-backup",
    }


def windows_paths(home: Path, environ: Optional[dict[str, str]] = None) -> dict[str, Path]:
    env = os.environ if environ is None else environ
    base = Path(env.get("LOCALAPPDATA", str(home / "AppData" / "Local")))
    install_dir = base / "WorkBuddyAutoCheckin"
    return {
        "install_dir": install_dir,
        "script": install_dir / SCRIPT_NAME,
        "log_dir": install_dir / "logs",
        "log": install_dir / "logs" / "checkin.log",
        "task_xml": install_dir / "task.xml",
        "backup": install_dir / "legacy-backup",
    }


def build_macos_plist(python: Path, script: Path, log: Path, hour: int, minute: int) -> dict:
    return {
        "Label": LABEL,
        "ProgramArguments": [str(python), str(script), "--log-file", str(log)],
        "WorkingDirectory": str(script.parent),
        # The core script writes one sanitized line to its own log. Redirecting
        # stdout to that same file would duplicate every result.
        "StandardOutPath": "/dev/null",
        "StandardErrorPath": "/dev/null",
        "RunAtLoad": False,
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "ProcessType": "Background",
    }


def build_windows_task_xml(
    python: Path,
    script: Path,
    log: Path,
    hour: int,
    minute: int,
    user_id: str,
) -> str:
    ns = "http://schemas.microsoft.com/windows/2004/02/mit/task"
    ET.register_namespace("", ns)

    def element(parent, name, text=None, **attrs):
        child = ET.SubElement(parent, f"{{{ns}}}{name}", attrs)
        if text is not None:
            child.text = str(text)
        return child

    task = ET.Element(f"{{{ns}}}Task", {"version": "1.4"})
    registration = element(task, "RegistrationInfo")
    element(registration, "Author", user_id)
    element(registration, "Description", "Daily WorkBuddy check-in for the current user")

    triggers = element(task, "Triggers")
    trigger = element(triggers, "CalendarTrigger")
    start = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    element(trigger, "StartBoundary", start.isoformat(timespec="seconds"))
    element(trigger, "Enabled", "true")
    schedule = element(trigger, "ScheduleByDay")
    element(schedule, "DaysInterval", "1")

    principals = element(task, "Principals")
    principal = element(principals, "Principal", id="Author")
    element(principal, "UserId", user_id)
    element(principal, "LogonType", "InteractiveToken")
    element(principal, "RunLevel", "LeastPrivilege")

    settings = element(task, "Settings")
    element(settings, "MultipleInstancesPolicy", "IgnoreNew")
    element(settings, "DisallowStartIfOnBatteries", "false")
    element(settings, "StopIfGoingOnBatteries", "false")
    element(settings, "AllowHardTerminate", "true")
    element(settings, "StartWhenAvailable", "true")
    element(settings, "RunOnlyIfNetworkAvailable", "true")
    element(settings, "AllowStartOnDemand", "true")
    element(settings, "Enabled", "true")
    element(settings, "Hidden", "false")
    element(settings, "WakeToRun", "false")
    element(settings, "ExecutionTimeLimit", "PT5M")
    element(settings, "Priority", "7")

    actions = element(task, "Actions", Context="Author")
    execute = element(actions, "Exec")
    element(execute, "Command", str(python))
    arguments = f'"{script}" --log-file "{log}"'
    element(execute, "Arguments", arguments)
    element(execute, "WorkingDirectory", str(script.parent))
    body = ET.tostring(task, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-16"?>\n' + body


def run(command: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=check, text=True, capture_output=capture)


def find_mac_legacy_jobs(launch_agents: Path) -> list[tuple[str, Path]]:
    jobs: list[tuple[str, Path]] = []
    if not launch_agents.is_dir():
        return jobs
    for plist_path in launch_agents.glob("*.plist"):
        try:
            with plist_path.open("rb") as handle:
                data = plistlib.load(handle)
            label = str(data.get("Label") or plist_path.stem)
            arguments = " ".join(str(item) for item in data.get("ProgramArguments", []))
        except (OSError, ValueError, TypeError):
            continue
        marker = f"{plist_path.name} {label} {arguments}".lower()
        if label != LABEL and "workbuddy" in marker and ("checkin" in marker or "signin" in marker):
            jobs.append((label, plist_path))
    return jobs


def backup_mac_legacy(paths: dict[str, Path], uid: int, dry_run: bool) -> list[str]:
    found = []
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = paths["backup"] / timestamp
    for label, plist in find_mac_legacy_jobs(paths["plist"].parent):
        found.append(label)
        if not dry_run:
            ensure_private_dir(destination)
            shutil.copy2(plist, destination / plist.name)
            run(["launchctl", "bootout", f"gui/{uid}/{label}"], check=False, capture=True)
            plist.unlink()
    return found


def install_macos(args, home: Path, source: Path) -> None:
    paths = mac_paths(home)
    hour, minute = args.time
    if args.dry_run:
        print(f"[DRY-RUN] 将安装到 {paths['install_dir']}")
        print(f"[DRY-RUN] 将创建 {paths['plist']}，每天 {hour:02d}:{minute:02d}")
        return
    for key in ("install_dir", "log_dir"):
        ensure_private_dir(paths[key])
    paths["plist"].parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, paths["script"])
    paths["script"].chmod(0o700)
    python = Path("/usr/bin/python3") if Path("/usr/bin/python3").is_file() else Path(sys.executable)
    plist = build_macos_plist(python, paths["script"], paths["log"], hour, minute)
    with paths["plist"].open("wb") as handle:
        plistlib.dump(plist, handle, sort_keys=True)

    uid = os.getuid()
    if args.replace_legacy:
        found = backup_mac_legacy(paths, uid, False)
        if found:
            print("已备份并停用旧任务：" + ", ".join(found))
    else:
        existing = [label for label, _ in find_mac_legacy_jobs(paths["plist"].parent)]
        if existing:
            print("警告：发现旧签到任务，可能造成重复请求：" + ", ".join(existing))
            print("确认后可重新运行并添加 --replace-legacy。")

    run(["launchctl", "bootout", f"gui/{uid}/{LABEL}"], check=False, capture=True)
    run(["launchctl", "bootstrap", f"gui/{uid}", str(paths["plist"])])
    print(f"安装完成：每天 {hour:02d}:{minute:02d} 自动运行")
    print(f"日志：{paths['log']}")
    if args.run_now:
        code = run([sys.executable, str(paths["script"]), "--log-file", str(paths["log"])], check=False).returncode
        if code != 0:
            raise RuntimeError(f"即时验证失败，退出码 {code}；请检查日志")


def windows_user_id() -> str:
    try:
        value = run(["whoami"], capture=True).stdout.strip()
        if value:
            return value
    except (OSError, subprocess.SubprocessError):
        pass
    return getpass.getuser()


def backup_windows_legacy(paths: dict[str, Path], dry_run: bool) -> list[str]:
    found = []
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = paths["backup"] / timestamp
    for task in LEGACY_WINDOWS_TASKS:
        query = run(["schtasks.exe", "/Query", "/TN", task, "/XML"], check=False, capture=True)
        if query.returncode == 0:
            found.append(task)
            if not dry_run:
                ensure_private_dir(destination)
                (destination / f"{task}.xml").write_text(query.stdout, encoding="utf-8")
                run(["schtasks.exe", "/Delete", "/TN", task, "/F"])
    return found


def install_windows(args, home: Path, source: Path) -> None:
    paths = windows_paths(home)
    hour, minute = args.time
    user_id = windows_user_id() if sys.platform.startswith("win") else "TEST\\User Name"
    xml = build_windows_task_xml(Path(sys.executable), paths["script"], paths["log"], hour, minute, user_id)
    if args.dry_run:
        ET.fromstring(xml)
        print(f"[DRY-RUN] Windows 任务 XML 验证通过，将安装到 {paths['install_dir']}")
        print(f"[DRY-RUN] 每天 {hour:02d}:{minute:02d}，错过后尽快补跑")
        return
    if not sys.platform.startswith("win"):
        raise RuntimeError("非 Windows 系统只能使用 --platform windows --dry-run 做结构验证")
    for key in ("install_dir", "log_dir"):
        ensure_private_dir(paths[key])
    shutil.copy2(source, paths["script"])
    # Task Scheduler expects its XML import in Windows "Unicode" format.
    # Python's utf-16 codec includes the required byte-order mark.
    paths["task_xml"].write_text(xml, encoding="utf-16")

    if args.replace_legacy:
        found = backup_windows_legacy(paths, False)
        if found:
            print("已备份并删除旧任务：" + ", ".join(found))

    run(["schtasks.exe", "/Create", "/TN", WINDOWS_TASK, "/XML", str(paths["task_xml"]), "/F"])
    print(f"安装完成：每天 {hour:02d}:{minute:02d} 自动运行")
    print(f"日志：{paths['log']}")
    if args.run_now:
        run(["schtasks.exe", "/Run", "/TN", WINDOWS_TASK])


def uninstall_macos(home: Path, dry_run: bool) -> None:
    paths = mac_paths(home)
    if dry_run:
        print(f"[DRY-RUN] 将移除 {paths['plist']} 和 {paths['script']}")
        return
    run(["launchctl", "bootout", f"gui/{os.getuid()}/{LABEL}"], check=False, capture=True)
    if paths["plist"].exists():
        paths["plist"].unlink()
    if paths["script"].exists():
        paths["script"].unlink()
    print("已卸载托管任务；日志和旧任务备份已保留。")


def uninstall_windows(home: Path, dry_run: bool) -> None:
    paths = windows_paths(home)
    if dry_run:
        print(f"[DRY-RUN] 将删除计划任务 {WINDOWS_TASK} 和 {paths['script']}")
        return
    if not sys.platform.startswith("win"):
        raise RuntimeError("只能在 Windows 上执行真实卸载")
    run(["schtasks.exe", "/Delete", "/TN", WINDOWS_TASK, "/F"], check=False)
    if paths["script"].exists():
        paths["script"].unlink()
    print("已卸载托管任务；日志和旧任务备份已保留。")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="安装 WorkBuddy 每日自动签到")
    parser.add_argument("--time", type=parse_time, default=parse_time("06:05"), help="每日时间 HH:MM")
    parser.add_argument("--run-now", action="store_true", help="安装后立即运行一次")
    parser.add_argument("--replace-legacy", action="store_true", help="备份并停用已知旧签到任务")
    parser.add_argument("--uninstall", action="store_true", help="卸载本工具管理的任务")
    parser.add_argument("--dry-run", action="store_true", help="只验证配置，不写入系统")
    parser.add_argument("--platform", choices=("auto", "macos", "windows"), default="auto")
    parser.add_argument("--home", type=Path, help=argparse.SUPPRESS)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    configure_utf8_console()
    args = build_parser().parse_args(argv)
    try:
        platform = detect_platform(args.platform)
        home = (args.home or Path.home()).expanduser().resolve()
        source = Path(__file__).resolve().with_name(SCRIPT_NAME)
        if not source.is_file():
            raise RuntimeError(f"缺少核心脚本：{source}")
        if args.uninstall:
            (uninstall_macos if platform == "macos" else uninstall_windows)(home, args.dry_run)
        else:
            (install_macos if platform == "macos" else install_windows)(args, home, source)
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"安装失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
