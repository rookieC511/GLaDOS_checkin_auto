#!/usr/bin/env python3
"""GLaDOS daily check-in for GitHub Actions and local schedulers."""

from __future__ import annotations

import os
import sys
import time
from typing import Any
from urllib.parse import urlparse

import requests


DEFAULT_BASE_URLS = (
    "https://glados.network",
    "https://glados.cloud",
    "https://glados.rocks",
)
CHECKIN_TOKENS = ("glados.network", "glados.cloud", "glados.one")
REQUEST_TIMEOUT = (10, 25)
MAX_ATTEMPTS = 3


def configure_console_encoding() -> None:
    """Keep Chinese logs readable in Windows schedulers and GitHub Actions."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (AttributeError, ValueError):
                pass


configure_console_encoding()


class CheckinError(RuntimeError):
    """A safe-to-print check-in failure."""


def split_cookies(value: str) -> list[str]:
    """Keep backward compatibility with the repository's `cookie&cookie` format."""
    normalized = value.replace("\r", "").replace("\n", "&")
    return [item.strip() for item in normalized.split("&") if item.strip()]


def configured_base_urls() -> list[str]:
    preferred = os.environ.get("GLADOS_BASE_URL", "").strip().rstrip("/")
    candidates = ([preferred] if preferred else []) + list(DEFAULT_BASE_URLS)
    return list(dict.fromkeys(url for url in candidates if url))


def request_headers(base_url: str, cookie: str) -> dict[str, str]:
    return {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "content-type": "application/json;charset=UTF-8",
        "cookie": cookie,
        "origin": base_url,
        "referer": f"{base_url}/console/checkin",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/144.0.0.0 Safari/537.36"
        ),
    }


def request_json(session: requests.Session, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
    last_error = "unknown error"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = session.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("response is not a JSON object")
            return payload
        except (requests.RequestException, ValueError) as exc:
            last_error = exc.__class__.__name__
            if attempt < MAX_ATTEMPTS:
                time.sleep(attempt)
    host = urlparse(url).netloc or "GLaDOS"
    raise CheckinError(f"{host} 请求连续失败（{last_error}）")


def get_status(session: requests.Session, base_url: str, cookie: str) -> dict[str, Any]:
    payload = request_json(
        session,
        "GET",
        f"{base_url}/api/user/status",
        headers=request_headers(base_url, cookie),
    )
    data = payload.get("data")
    if isinstance(data, dict):
        return data

    message = str(payload.get("message") or "")
    if payload.get("code") == -2 or "没有权限" in message:
        raise CheckinError("Cookie 已过期或无权限")
    raise CheckinError("账户状态响应缺少 data 字段")


def find_working_base_url(session: requests.Session, cookie: str) -> tuple[str, dict[str, Any]]:
    failures: list[str] = []
    for base_url in configured_base_urls():
        try:
            return base_url, get_status(session, base_url, cookie)
        except CheckinError as exc:
            failures.append(f"{urlparse(base_url).netloc}: {exc}")
    raise CheckinError("；".join(failures))


def is_successful_checkin(payload: dict[str, Any]) -> bool:
    message = str(payload.get("message") or "").strip().lower()
    if payload.get("code") == 0:
        return True
    if "please checkin via" in message:
        return False
    positive_markers = ("got", "repeat", "already", "checked in", "success", "签到成功", "已签到")
    negative_markers = ("fail", "error", "invalid", "expired", "没有权限")
    return (
        message.startswith("checkin")
        and not any(marker in message for marker in negative_markers)
    ) or any(marker in message for marker in positive_markers)


def check_in(session: requests.Session, base_url: str, cookie: str) -> str:
    errors: list[str] = []
    for token in CHECKIN_TOKENS:
        payload = request_json(
            session,
            "POST",
            f"{base_url}/api/user/checkin",
            headers=request_headers(base_url, cookie),
            json={"token": token},
        )
        message = str(payload.get("message") or "unknown response").strip()
        if payload.get("code") == -2 or "没有权限" in message:
            raise CheckinError("Cookie 已过期或无权限")
        if is_successful_checkin(payload):
            return message
        errors.append(f"{token}: {message}")
    raise CheckinError("所有签到 token 均失败：" + "；".join(errors))


def format_status(status: dict[str, Any]) -> str:
    fields: list[str] = []
    left_days = status.get("leftDays")
    if left_days not in (None, ""):
        fields.append(f"剩余 {str(left_days).split('.')[0]} 天")
    points = status.get("points")
    if points not in (None, ""):
        fields.append(f"积分 {points}")
    return "，".join(fields) if fields else "账户状态正常"


def check_account(index: int, cookie: str) -> str:
    with requests.Session() as session:
        base_url, _ = find_working_base_url(session, cookie)
        message = check_in(session, base_url, cookie)
        status = get_status(session, base_url, cookie)
    return f"账号 {index}: {message}；{format_status(status)}"


def send_pushplus(token: str, lines: list[str], success: bool) -> None:
    if not token:
        return
    title = "GLaDOS 签到成功" if success else "GLaDOS 签到失败"
    try:
        response = requests.post(
            "https://www.pushplus.plus/send",
            json={"token": token, "title": title, "content": "\n".join(lines), "template": "txt"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"[WARN] PushPlus 推送失败：{exc.__class__.__name__}")


def main() -> int:
    cookies = split_cookies(os.environ.get("GLADOS_COOKIE", ""))
    if not cookies:
        print("[ERROR] 未找到 GLADOS_COOKIE。请检查 GitHub Actions Secret。")
        return 1

    results: list[str] = []
    failures = 0
    for index, cookie in enumerate(cookies, start=1):
        print(f"[INFO] 正在处理账号 {index}...")
        try:
            result = check_account(index, cookie)
            print(f"[OK] {result}")
            results.append(f"[OK] {result}")
        except CheckinError as exc:
            failures += 1
            result = f"账号 {index}: {exc}"
            print(f"[ERROR] {result}")
            results.append(f"[ERROR] {result}")

    send_pushplus(os.environ.get("PUSHPLUS_TOKEN", "").strip(), results, failures == 0)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
