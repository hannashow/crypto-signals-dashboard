"""透過 LINE Messaging API 發送推播訊息。

需要兩個環境變數(在 GitHub Actions 以 Secrets 提供):
  LINE_CHANNEL_ACCESS_TOKEN — LINE Developers Console 取得的 Channel access token
  LINE_USER_ID              — 接收訊息的使用者 ID
"""

import os
import re

import requests

PUSH_ENDPOINT = "https://api.line.me/v2/bot/message/push"

# LINE user ID 格式:U 開頭 + 32 個十六進位字元
USER_ID_PATTERN = re.compile(r"^U[0-9a-f]{32}$")


def send_line_message(text: str) -> None:
    """發送一則文字訊息。憑證缺失或 API 回應失敗時拋出例外。"""
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.environ.get("LINE_USER_ID")
    if not token or not user_id:
        raise RuntimeError(
            "缺少 LINE_CHANNEL_ACCESS_TOKEN 或 LINE_USER_ID 環境變數"
        )
    if not USER_ID_PATTERN.match(user_id):
        raise RuntimeError(
            "LINE_USER_ID 格式不正確,應為 U 開頭加 32 個十六進位字元。"
            "請至 LINE Developers Console 的 Basic settings 分頁底部複製 Your user ID"
            "(不是 Channel ID,也不是 @ 開頭的 Basic ID)"
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
    if not response.ok:
        # LINE 會在回應內容說明失敗原因,一併拋出方便排查
        raise RuntimeError(
            f"LINE API 回應 {response.status_code}:{response.text}"
        )
