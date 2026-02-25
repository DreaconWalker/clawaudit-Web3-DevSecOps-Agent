---
name: telegram
description: Send a message to the developer via Telegram. Use when the user or task asks to send a Telegram alert, notify the developer, or send a secure alert to the phone. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in the container environment for the script to work.
version: 1.0.0
metadata:
  openclaw:
    primaryEnv: TELEGRAM_BOT_TOKEN
---

# Telegram skill – send alert via custom Python script

You MUST use this skill by **actually running** the Python script. Do NOT reply with "I have attempted to send" or "I have sent the alert" without invoking the **exec** tool first.

## How to send a message

1. Use the **exec** tool (never skip this).
2. Run this exact pattern (replace the message text as needed):

   ```
   python3 /home/node/.openclaw/skills/telegram/telegram.py "<MESSAGE>"
   ```

   Example alert message: `CRITICAL ALERT: Vulnerability detected. Auto-remediation patch generated. Check your ClawAudit Sentinel dashboard immediately.`

3. The script reads `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` from the environment.

## Rules

- **Always** call the **exec** tool with the `python3` command above. No exceptions.
- **Never** claim you sent a Telegram message without having run the command and received a successful tool result.
- If the script fails, report the error from the tool result to the user.
