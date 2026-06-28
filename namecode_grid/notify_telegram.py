#!/usr/bin/env python3
"""Send a Telegram message (daily status notification).

Env:
  TELEGRAM_BOT_TOKEN  bot token from @BotFather
  TELEGRAM_CHAT_ID    chat id to send to (your user id, or a channel/group id)
  MESSAGE             message text (or pass as argv[1])

No-ops quietly if the bot token / chat id are not configured.
"""
import os, sys, requests


def main():
    tok = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    msg = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("MESSAGE", "")
    if not tok or not chat:
        print("Telegram not configured; skipping notification.")
        return
    payload = {"chat_id": chat, "text": msg or "(empty)", "disable_web_page_preview": True}
    btn_url = os.environ.get("BUTTON_URL")
    if btn_url:  # inline link button (e.g. the published Instagram post)
        payload["reply_markup"] = {"inline_keyboard": [[
            {"text": os.environ.get("BUTTON_TEXT", "Open"), "url": btn_url}]]}
    r = requests.post(f"https://api.telegram.org/bot{tok}/sendMessage", json=payload, timeout=30)
    print("telegram:", r.status_code, r.text[:200])


if __name__ == "__main__":
    main()
