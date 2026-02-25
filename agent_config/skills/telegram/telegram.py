#!/usr/bin/env python3
"""
Send a message to the developer via Telegram Bot API.
Reads TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from the environment.
Message is passed as arguments: python3 telegram.py "your message here"
"""
import os
import sys
import urllib.request
import urllib.parse
import json

def main():
    token = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    if not token or not chat_id:
        print("ERROR: Telegram credentials missing. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in the environment.", file=sys.stderr)
        sys.exit(1)
    message = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else ""
    if not message:
        print("ERROR: No message provided. Usage: python3 telegram.py \"your message\"", file=sys.stderr)
        sys.exit(1)
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            out = json.loads(resp.read().decode())
            if not out.get("ok"):
                print(f"ERROR: Telegram API: {out}", file=sys.stderr)
                sys.exit(1)
            print("OK: Message sent to Telegram.")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
