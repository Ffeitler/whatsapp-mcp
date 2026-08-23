#!/usr/bin/env python3
"""
whatsapp-cmd-watcher.py — Standalone command watcher for WhatsApp self-chat.
Runs as a separate daemon alongside whatsapp-bot.sh.
Polls the bridge for new self-chat messages, detects commands, dispatches to vault-commands.py.

Commands recognized (case-insensitive, at start of message):
  done A-NNN [outcome]
  snooze A-NNN <days>
  add <description>
  note <text>
  status A-NNN
  find <query>
  help
"""

import re, json, time, subprocess, sys, urllib.request
from datetime import datetime
from pathlib import Path

BRIDGE_URL   = "http://localhost:8080"
SELF_CHAT    = "211626041049100@lid"
VAULT_CMD    = Path.home() / "Desktop" / "whatsapp-mcp" / "vault-commands.py"
STATE_FILE   = Path.home() / "Desktop" / "whatsapp-mcp" / ".cmd-watcher-state.json"
POLL_INTERVAL = 5  # seconds
BRIDGE_URL_SEND = f"{BRIDGE_URL}/api/send"

COMMANDS = {"done", "snooze", "add", "note", "status", "find", "help"}

# ── Bridge API probe ──────────────────────────────────────────────────────────

def probe_message_endpoints():
    """Try common bridge API patterns to find messages endpoint."""
    candidates = [
        f"{BRIDGE_URL}/api/messages?jid={SELF_CHAT}&limit=10",
        f"{BRIDGE_URL}/api/messages/{SELF_CHAT}?limit=10",
        f"{BRIDGE_URL}/messages?jid={SELF_CHAT}",
        f"{BRIDGE_URL}/api/chats/{SELF_CHAT}/messages",
        f"{BRIDGE_URL}/api/inbox",
    ]
    for url in candidates:
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as r:
                body = r.read().decode()
                if r.status == 200 and ('"messages"' in body or '"id"' in body or '"text"' in body):
                    print(f"[watcher] Found messages endpoint: {url}", flush=True)
                    return url
        except:
            pass
    return None

def fetch_messages(endpoint):
    """Fetch recent messages from the bridge."""
    try:
        req = urllib.request.Request(endpoint, method="GET")
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"[watcher] fetch error: {e}", flush=True)
        return None

def send_whatsapp(msg):
    payload = json.dumps({"recipient": SELF_CHAT, "message": msg}).encode()
    req = urllib.request.Request(BRIDGE_URL_SEND, data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status

# ── State: track last seen message id/timestamp ───────────────────────────────

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_id": None, "last_ts": 0, "seen_ids": []}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state))

# ── Command dispatch ──────────────────────────────────────────────────────────

def dispatch(msg_text):
    """Parse command from message text and call vault-commands.py."""
    text = msg_text.strip()
    parts = text.split()
    if not parts:
        return None

    cmd = parts[0].lower()
    if cmd not in COMMANDS:
        return None

    if cmd == "help":
        return (
            "📖 *Available commands*\n"
            "  done A-NNN [outcome] — mark action complete\n"
            "  snooze A-NNN <days> — push due date\n"
            "  add <description> — create new action\n"
            "  note <text> — capture to raw/\n"
            "  status A-NNN — show action detail\n"
            "  find <query> — search vault"
        )

    # delegate to vault-commands.py
    try:
        result = subprocess.run(
            [sys.executable, str(VAULT_CMD), cmd] + parts[1:],
            capture_output=True, text=True, timeout=15
        )
        # vault-commands.py sends its own WhatsApp reply; we just log stdout
        print(f"[watcher] {cmd} result: {result.stdout.strip()}", flush=True)
        if result.returncode != 0:
            print(f"[watcher] stderr: {result.stderr.strip()}", flush=True)
        return None  # vault-commands.py already sent the reply
    except Exception as e:
        return f"❌ Command error: {e}"

# ── Message extraction ────────────────────────────────────────────────────────

def extract_messages(data):
    """Normalize bridge API response to list of {id, ts, text} dicts."""
    msgs = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("messages", data.get("data", []))
    else:
        return msgs

    for item in items:
        if not isinstance(item, dict):
            continue
        # common field names across bridge implementations
        msg_id = item.get("id") or item.get("ID") or item.get("message_id")
        ts = item.get("timestamp") or item.get("ts") or item.get("time") or 0
        text = (
            item.get("text") or
            item.get("body") or
            item.get("content") or
            item.get("Message", {}).get("Conversation") or
            item.get("message", {}).get("text") or
            ""
        )
        # only include self-sent messages (from_me)
        from_me = (
            item.get("from_me") or
            item.get("fromMe") or
            item.get("IsFromMe") or
            item.get("is_from_me")
        )
        if text and from_me:
            msgs.append({"id": msg_id, "ts": ts, "text": text})

    return msgs

# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    print("[watcher] Starting WhatsApp command watcher...", flush=True)

    # Check vault-commands.py exists
    if not VAULT_CMD.exists():
        print(f"[watcher] ERROR: vault-commands.py not found at {VAULT_CMD}", flush=True)
        print("[watcher] Run install-bot-commands.command first.", flush=True)
        sys.exit(1)

    # Probe for message endpoint
    endpoint = probe_message_endpoints()
    if not endpoint:
        print("[watcher] WARNING: Could not find messages endpoint.", flush=True)
        print("[watcher] Bridge may use webhook push instead of polling.", flush=True)
        print("[watcher] Will retry every 60s...", flush=True)
        # Keep trying — bridge might not be ready yet
        while True:
            time.sleep(60)
            endpoint = probe_message_endpoints()
            if endpoint:
                break

    print(f"[watcher] Polling {endpoint} every {POLL_INTERVAL}s", flush=True)
    state = load_state()

    while True:
        try:
            data = fetch_messages(endpoint)
            if data:
                msgs = extract_messages(data)
                for msg in msgs:
                    mid = str(msg["id"]) if msg["id"] else f"ts_{msg['ts']}"
                    if mid in state.get("seen_ids", []):
                        continue

                    # Check if it's a command
                    text = msg["text"].strip()
                    first_word = text.split()[0].lower() if text.split() else ""
                    if first_word in COMMANDS:
                        print(f"[watcher] Command detected: {text[:60]}", flush=True)
                        reply = dispatch(text)
                        if reply:
                            send_whatsapp(reply)

                    # Track seen
                    seen = state.get("seen_ids", [])
                    seen.append(mid)
                    if len(seen) > 500:
                        seen = seen[-200:]
                    state["seen_ids"] = seen
                    save_state(state)

        except KeyboardInterrupt:
            print("[watcher] Stopped.", flush=True)
            sys.exit(0)
        except Exception as e:
            print(f"[watcher] Loop error: {e}", flush=True)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
