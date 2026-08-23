#!/usr/bin/env python3
"""
Morning Briefing — WhatsApp self-chat push
Runs daily at 7am via LaunchAgent.
Reads wiki/actions.md for due/overdue items + context/priorities.md for focus.
Sends a concise summary to WhatsApp self-chat.
"""

import re, json, urllib.request
from datetime import date, datetime
from pathlib import Path

VAULT        = Path.home() / "Desktop" / "Obsidian"
ACTIONS_FILE = VAULT / "wiki" / "actions.md"
BRIDGE_URL   = "http://localhost:8080/api/send"
SELF_CHAT    = "211626041049100@lid"

PRIORITY_EMOJI = {"🔺": "🔺", "⏫": "⏫", "🔼": ""}

def parse_actions():
    """
    Extract open actions with due dates.
    Returns (overdue, due_today, due_soon) — lists of (id, text, priority) tuples.
    """
    text = ACTIONS_FILE.read_text(encoding="utf-8")
    today = date.today()
    overdue, due_today, due_soon = [], [], []

    # Match open action items: - [ ] **[A-NNN]** ...
    for line in text.splitlines():
        if not line.strip().startswith("- [ ]"):
            continue
        # Extract action ID
        id_match = re.search(r'\[A-(\d+)\]', line)
        if not id_match:
            continue
        action_id = f"A-{id_match.group(1)}"

        # Extract due date 📅 YYYY-MM-DD
        date_match = re.search(r'📅\s*(\d{4}-\d{2}-\d{2})', line)
        if not date_match:
            continue
        due = date.fromisoformat(date_match.group(1))

        # Extract priority emoji
        priority = ""
        if "🔺" in line:
            priority = "🔺"
        elif "⏫" in line:
            priority = "⏫"

        # Extract short description — text between **[A-NNN]** and first —
        desc_match = re.search(r'\*\*\[A-\d+\]\*\*\s*\*\*(.+?)\*\*', line)
        if desc_match:
            desc = desc_match.group(1).strip()
        else:
            after_id = line[line.find(action_id) + len(action_id):]
            desc = re.sub(r'\*+', '', after_id).strip()[:80].strip("* —")

        delta = (due - today).days
        entry = (action_id, desc[:60], priority, due)

        if delta < 0:
            overdue.append(entry)
        elif delta == 0:
            due_today.append(entry)
        elif delta <= 3:
            due_soon.append(entry)

    return overdue, due_today, due_soon

def build_message():
    today = date.today()
    dow = today.strftime("%A")
    date_str = today.strftime("%b %-d")
    now_str = datetime.now().strftime("%H:%M ET")

    overdue, due_today, due_soon = parse_actions()

    lines = []
    lines.append(f"☀️ *Good morning — {dow}, {date_str}*")
    lines.append("")

    # Overdue — show urgent only, summarize the rest
    if overdue:
        urgent_overdue = [x for x in overdue if x[2] in ("🔺", "⏫")]
        quiet_overdue  = [x for x in overdue if x[2] not in ("🔺", "⏫")]
        lines.append(f"🚨 *Overdue ({len(overdue)})*")
        for aid, desc, pri, due in sorted(urgent_overdue, key=lambda x: x[3]):
            days_ago = (date.today() - due).days
            lines.append(f"  {pri} [{aid}] {desc} (+{days_ago}d)")
        if quiet_overdue:
            lines.append(f"  ▪ +{len(quiet_overdue)} more (open Brain to review)")
        lines.append("")

    # Due today — urgent first
    if due_today:
        lines.append(f"📌 *Due today ({len(due_today)})*")
        pri_order = {"🔺": 0, "⏫": 1, "": 2}
        for aid, desc, pri, _ in sorted(due_today, key=lambda x: pri_order.get(x[2], 2)):
            lines.append(f"  {pri or '▪'} [{aid}] {desc}")
        lines.append("")

    # Due in next 3 days
    if due_soon:
        lines.append(f"⏳ *Due soon ({len(due_soon)})*")
        for aid, desc, pri, due in sorted(due_soon, key=lambda x: x[3]):
            days_str = "tomorrow" if (due - date.today()).days == 1 else due.strftime("%b %-d")
            lines.append(f"  {pri or '▪'} [{aid}] {desc} — {days_str}")
        lines.append("")

    if not overdue and not due_today and not due_soon:
        lines.append("✅ Nothing urgent in the next 3 days.")
        lines.append("")

    lines.append(f"_⏱ {now_str}_")
    return "\n".join(lines)

def send_whatsapp(msg):
    payload = json.dumps({"recipient": SELF_CHAT, "message": msg}).encode()
    req = urllib.request.Request(
        BRIDGE_URL, data=payload,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status

if __name__ == "__main__":
    msg = build_message()
    print(msg)
    print()
    status = send_whatsapp(msg)
    print(f"Sent to WhatsApp (status {status})")
