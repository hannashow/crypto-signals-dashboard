"""透過 LINE Messaging API 發送推播訊息。

需要兩個環境變數(在 GitHub Actions 以 Secrets 提供):
  LINE_CHANNEL_ACCESS_TOKEN — LINE Developers Console 取得的 Channel access token
  LINE_USER_ID              — 接收訊息的使用者 ID
"""

import os

import requests

PUSH_ENDPOINT = "https://api.line.me/v2/bot/message/push"


def send_line_message(text: str) -> None:
    """發送一則文字訊息。憑證缺失或 API 回應失敗時拋出例外。"""
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.environ.get("LINE_USER_ID")
    if not token or not user_id:
        raise RuntimeError(
            "缺少 LINE_CHANNEL_ACCESS_TOKEN 或 LINE_USER_ID 環境變數"
        )

    response = requests.post(
        PUSH_ENDPOINT,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"to": user_id, "messages": [{"type": "text", "text": text}]},
        timeout=15,
    )
    response.raise_for_status()
