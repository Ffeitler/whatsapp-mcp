#!/usr/bin/env python3
"""
vault-checkin.py — Daily action check-in via WhatsApp self-chat.
Runs daily (separate from morning briefing, e.g. at 10am).

Picks the top overdue or stale actions and asks about each one:
  "A-135: Fort Myers RSVP — still open? Reply: done A-135 / snooze A-135 7 / note A-135 <info>"

Prioritizes:
  1. Overdue urgent (🔺/⏫) with no recent update
  2. Overdue normal with no due date change in 14+ days
  3. Actions with no due date at all (needs triage)

Max 3 questions per day to avoid noise.
"""

import re, json, urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

VAULT        = Path.home() / "Desktop" / "Obsidian"
ACTIONS_FILE = VAULT / "wiki" / "actions.md"
STATE_FILE   = Path.home() / "Desktop" / "whatsapp-mcp" / ".checkin-state.json"
BRIDGE_URL   = "http://localhost:8080/api/send"
SELF_CHAT    = "211626041049100@lid"
TODAY        = date.today()
MAX_QUESTIONS = 3

def send_whatsapp(msg):
    payload = json.dumps({"recipient": SELF_CHAT, "message": msg}).encode()
    req = urllib.request.Request(BRIDGE_URL, data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"asked_today": [], "last_run": None, "asked_ever": {}}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, default=str))

def parse_open_actions():
    """Return list of action dicts from actions.md, open only."""
    text = ACTIONS_FILE.read_text(encoding="utf-8")
    actions = []

    for line in text.splitlines():
        if not line.strip().startswith("- [ ]"):
            continue

        id_match = re.search(r'\[A-(\d+)\]', line)
        if not id_match:
            continue
        action_id = f"A-{id_match.group(1)}"

        desc_match = re.search(r'\*\*\[A-\d+\]\*\*\s*\*\*(.+?)\*\*', line)
        desc = desc_match.group(1).strip()[:60] if desc_match else action_id

        date_match = re.search(r'📅\s*(\d{4}-\d{2}-\d{2})', line)
        due = date.fromisoformat(date_match.group(1)) if date_match else None

        priority = "🔺" if "🔺" in line else ("⏫" if "⏫" in line else "🔼" if "🔼" in line else "")

        actions.append({
            "id": action_id,
            "desc": desc,
            "due": due,
            "priority": priority,
            "line": line,
            "days_overdue": (TODAY - due).days if due and due < TODAY else 0,
            "no_date": due is None,
        })

    return actions

def score_action(a, asked_ever):
    """Higher score = more urgent to ask about."""
    score = 0

    # Overdue
    if a["days_overdue"] > 0:
        score += a["days_overdue"] * 2
        if a["priority"] in ("🔺", "⏫"):
            score += 20

    # No due date = needs triage
    if a["no_date"]:
        score += 5

    # Reduce score if asked recently (avoid nagging)
    last_asked = asked_ever.get(a["id"])
    if last_asked:
        days_since = (TODAY - date.fromisoformat(last_asked)).days
        if days_since < 3:
            score -= 50   # Skip if asked in last 3 days
        elif days_since < 7:
            score -= 10

    return score

def format_question(a):
    """Format a WhatsApp check-in question for this action."""
    if a["days_overdue"] > 0:
        header = f"⏰ *[{a['id']}] overdue {a['days_overdue']}d*"
    elif a["no_date"]:
        header = f"📋 *[{a['id']}] needs a due date*"
    else:
        header = f"📌 *[{a['id']}]*"

    desc = a["desc"]
    lines = [
        header,
        f"_{desc}_",
        "",
        "Still open? Reply:",
        f"  `done {a['id']}` — mark complete",
        f"  `snooze {a['id']} 7` — push 1 week",
        f"  `note {a['id']} <update>` — add info",
    ]
    return "\n".join(lines)

def main():
    state = load_state()
    today_str = TODAY.isoformat()

    # Reset daily asked list if it's a new day
    if state.get("last_run") != today_str:
        state["asked_today"] = []
        state["last_run"] = today_str

    asked_today = set(state.get("asked_today", []))
    asked_ever = state.get("asked_ever", {})

    # Already asked max questions today
    if len(asked_today) >= MAX_QUESTIONS:
        print(f"Already asked {MAX_QUESTIONS} questions today. Done.")
        return

    actions = parse_open_actions()

    # Score and sort
    scored = [(score_action(a, asked_ever), a) for a in actions]
    scored.sort(key=lambda x: -x[0])

    questions_sent = 0
    for score, action in scored:
        if questions_sent >= (MAX_QUESTIONS - len(asked_today)):
            break
        if score <= 0:
            break
        if action["id"] in asked_today:
            continue

        msg = format_question(action)
        try:
            send_whatsapp(msg)
            print(f"Asked about {action['id']} (score {score})")
            asked_today.add(action["id"])
            asked_ever[action["id"]] = today_str
            questions_sent += 1
        except Exception as e:
            print(f"WhatsApp error: {e}")

    state["asked_today"] = list(asked_today)
    state["asked_ever"] = asked_ever
    save_state(state)

    if questions_sent == 0:
        print("No actions needed check-in today.")

if __name__ == "__main__":
    main()
