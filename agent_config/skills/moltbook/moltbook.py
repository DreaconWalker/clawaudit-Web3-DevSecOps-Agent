#!/usr/bin/env python3
"""
Post to Moltbook (https://www.moltbook.com) API.
Reads MOLTBOOK_API_KEY from the environment; optional MOLTBOOK_SUBMOLT (default: lablab).
Usage: python3 moltbook.py "content"
   or: python3 moltbook.py "submolt_name" "content"
   or: python3 moltbook.py "submolt_name" "title" "content"
"""
import os
import sys
import urllib.request
import json

def main():
    api_key = (os.environ.get("MOLTBOOK_API_KEY") or "").strip()
    default_submolt = (os.environ.get("MOLTBOOK_SUBMOLT") or "lablab").strip()
    if not api_key:
        print("ERROR: MOLTBOOK_API_KEY missing in environment.", file=sys.stderr)
        sys.exit(1)
    args = [a.strip() for a in sys.argv[1:] if a.strip()]
    if len(args) == 1:
        submolt, title, content = default_submolt, "ClawAudit Sentinel", args[0]
    elif len(args) == 2:
        submolt, content = args[0], args[1]
        title = "ClawAudit Sentinel"
    elif len(args) >= 3:
        submolt, title, content = args[0], args[1], " ".join(args[2:])
    else:
        print("ERROR: Usage: python3 moltbook.py \"content\" or python3 moltbook.py \"submolt\" \"content\"", file=sys.stderr)
        sys.exit(1)
    url = "https://www.moltbook.com/api/v1/posts"
    payload = {
        "submolt_name": submolt,
        "title": title,
        "content": content,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            out = json.loads(resp.read().decode())
            if out.get("verification_required") or out.get("challenge"):
                print("OK: Post created; verification may be required.", out, file=sys.stderr)
            else:
                print("OK: Posted to Moltbook submolt", submolt)
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"ERROR: Moltbook API {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
