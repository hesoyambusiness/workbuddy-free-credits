#!/usr/bin/env python3
"""One-account, once-daily WorkBuddy check-in client.

The program reads the current user's existing WorkBuddy credential file at run
time. It never prints or copies the token and has no telemetry.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping, Optional

VERSION = "1.0.0"
CHECKIN_API = "https://copilot.tencent.com/v2/billing/meter/daily-checkin"
KNOWN_OK_MESSAGES = ("今天已签到", "请明天再来", "请求处理中", "请勿重复操作")


def configure_utf8_console() -> None:
    """Keep Chinese status output safe on legacy Windows console encodings."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass


def platform_key(value: Optional[str] = None) -> str:
    value = value or sys.platform
    if value.startswith("win"):
        return "windows"
    if value == "darwin":
        return "macos"
    return "other"


def candidate_token_files(
    platform: Optional[str] = None,
    environ: Optional[Mapping[str, str]] = None,
    home: Optional[Path] = None,
) -> list[Path]:
    """Return ordered credential candidates without reading their contents."""
    env = dict(os.environ if environ is None else environ)
    home = Path.home() if home is None else Path(home)
    candidates: list[Path] = []

    for key in ("WORKBUDDY_TOKEN_FILE", "WORKBUDDY_INFO_PATH"):
        if env.get(key):
            candidates.append(Path(env[key]).expanduser())

    kind = platform_key(platform)
    app_names = ("CodeBuddyExtension", "WorkBuddyExtension", "WorkBuddy", "CodeBuddy")
    auth_names = ("auth", "Auth")

    if kind == "macos":
        base = home / "Library" / "Application Support"
        for app_name in app_names:
            for auth_name in auth_names:
                candidates.append(
                    base / app_name / "Data" / "Public" / auth_name / "workbuddy-desktop.info"
                )
    elif kind == "windows":
        bases: list[Path] = []
        if env.get("LOCALAPPDATA"):
            bases.append(Path(env["LOCALAPPDATA"]))
        if env.get("APPDATA"):
            bases.append(Path(env["APPDATA"]))
        if not bases:
            bases.extend((home / "AppData" / "Local", home / "AppData" / "Roaming"))
        for base in bases:
            for app_name in app_names:
                for auth_name in auth_names:
                    candidates.append(
                        base / app_name / "Data" / "Public" / auth_name / "workbuddy-desktop.info"
                    )

    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        marker = os.path.normcase(str(path))
        if marker not in seen:
            seen.add(marker)
            unique.append(path)
    return unique


def find_token_file(candidates: Iterable[Path]) -> Path:
    tried = []
    for path in candidates:
        tried.append(str(path))
        if path.is_file():
            return path
    lines = "\n".join(f"  - {item}" for item in tried) or "  - 没有可用候选路径"
    raise FileNotFoundError(
        "找不到 WorkBuddy 登录文件。请先安装并登录 WorkBuddy。已检查：\n" + lines
    )


def load_token(path: Path) -> str:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        token = data["auth"]["accessToken"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RuntimeError(f"WorkBuddy 登录文件无法读取或格式不兼容：{type(exc).__name__}") from exc
    if not isinstance(token, str) or len(token) < 20:
        raise RuntimeError("WorkBuddy 登录文件中没有有效的 accessToken")
    return token


def state_dir(platform: Optional[str] = None, home: Optional[Path] = None) -> Path:
    home = Path.home() if home is None else Path(home)
    if platform_key(platform) == "windows":
        base = os.environ.get("LOCALAPPDATA")
        return (Path(base) if base else home / "AppData" / "Local") / "WorkBuddyAutoCheckin"
    return home / ".local" / "state" / "workbuddy-auto-checkin"


@contextmanager
def single_instance(lock_path: Path, stale_seconds: int = 600):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        lock_path.parent.chmod(0o700)
    except OSError:
        pass
    if lock_path.exists() and time.time() - lock_path.stat().st_mtime > stale_seconds:
        try:
            lock_path.unlink()
        except OSError:
            pass
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise RuntimeError("另一个签到进程正在运行，本次已跳过") from exc
    try:
        os.write(fd, str(os.getpid()).encode("ascii"))
        os.close(fd)
        yield
    finally:
        try:
            lock_path.unlink()
        except OSError:
            pass


def clean_message(value: object) -> str:
    text = str(value or "未知返回").replace("\r", " ").replace("\n", " ").strip()
    return text[:240]


def parse_response(raw: bytes) -> dict:
    try:
        value = json.loads(raw.decode("utf-8", errors="replace"))
    except ValueError as exc:
        raise RuntimeError("服务返回了无法识别的数据") from exc
    if not isinstance(value, dict):
        raise RuntimeError("服务返回格式不兼容")
    return value


def is_idempotent_message(message: str) -> bool:
    return any(marker in message for marker in KNOWN_OK_MESSAGES)


def perform_checkin(token: str, timeout: float = 15.0) -> tuple[int, str]:
    request = urllib.request.Request(
        CHECKIN_API,
        data=b"{}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": f"workbuddy-auto-checkin/{VERSION}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = parse_response(response.read())
    except urllib.error.HTTPError as exc:
        try:
            result = parse_response(exc.read())
            message = clean_message(result.get("msg"))
        except RuntimeError:
            message = f"HTTP {exc.code}"
        if exc.code == 400 and is_idempotent_message(message):
            return 0, message
        if exc.code in (401, 403):
            return 3, "登录凭证已失效或无权限，请重新登录 WorkBuddy"
        if exc.code == 429:
            return 4, "请求过于频繁，本次不再重试"
        return 4, f"签到请求失败：{message}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = clean_message(getattr(exc, "reason", type(exc).__name__))
        return 5, f"网络请求失败：{reason}"

    if result.get("code") == 0:
        data = result.get("data") if isinstance(result.get("data"), dict) else {}
        credit = data.get("credit", 0)
        streak = data.get("streak_days", 0)
        return 0, f"领取成功：获得 {credit} 积分，连续 {streak} 天"
    message = clean_message(result.get("msg"))
    if is_idempotent_message(message):
        return 0, message
    return 4, f"签到未完成：{message}"


def emit(message: str, log_file: Optional[Path] = None, error: bool = False) -> None:
    line = f"[{datetime.now().isoformat(sep=' ', timespec='seconds')}] {message}"
    print(line, file=sys.stderr if error else sys.stdout)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            log_file.parent.chmod(0o700)
        except OSError:
            pass
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        try:
            log_file.chmod(0o600)
        except OSError:
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WorkBuddy 每日自动签到")
    parser.add_argument("--dry-run", action="store_true", help="只检查登录文件，不发送签到请求")
    parser.add_argument("--token-file", type=Path, help="显式指定 WorkBuddy 登录文件")
    parser.add_argument("--log-file", type=Path, help="将脱敏结果追加到指定日志")
    parser.add_argument("--version", action="version", version=VERSION)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    configure_utf8_console()
    args = build_parser().parse_args(argv)
    candidates = [args.token_file.expanduser()] if args.token_file else candidate_token_files()
    try:
        token_path = find_token_file(candidates)
        token = load_token(token_path)
    except (FileNotFoundError, RuntimeError) as exc:
        emit(f"错误：{exc}", args.log_file, error=True)
        return 2

    if args.dry_run:
        emit("检查通过：已找到可读取的 WorkBuddy 登录文件；未发送网络请求", args.log_file)
        return 0

    try:
        with single_instance(state_dir() / "checkin.lock"):
            code, message = perform_checkin(token)
    except RuntimeError as exc:
        emit(str(exc), args.log_file)
        return 0
    emit(message, args.log_file, error=code != 0)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
