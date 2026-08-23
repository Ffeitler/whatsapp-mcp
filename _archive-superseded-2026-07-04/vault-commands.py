#!/usr/bin/env python3
"""
vault-commands.py — WhatsApp self-chat command handler
Called by whatsapp-bot.sh when a command is detected in self-chat.

Usage: python3 vault-commands.py <command> [args...]

Commands:
  done A-NNN [outcome text]   — mark action complete
  snooze A-NNN <days>         — push due date N days
  add <description>           — create new action
  note <text>                 — append raw capture
  status A-NNN                — show action details
  find <query>                — search vault

Output: reply message to send back via WhatsApp
"""

import re, sys, json, urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

VAULT        = Path.home() / "Desktop" / "Obsidian"
ACTIONS_FILE = VAULT / "wiki" / "actions.md"
LOG_FILE     = VAULT / "wiki" / "log.md"
RAW_DIR      = VAULT / "raw"
BRIDGE_URL   = "http://localhost:8080/api/send"
SELF_CHAT    = "211626041049100@lid"
NOW_STR      = datetime.now().strftime("%Y-%m-%d %H:%M ET")
TODAY        = date.today().isoformat()

def send_whatsapp(msg):
    payload = json.dumps({"recipient": SELF_CHAT, "message": msg}).encode()
    req = urllib.request.Request(BRIDGE_URL, data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status

def append_log(entry):
    text = LOG_FILE.read_text(encoding="utf-8")
    log_entry = f"\n## [{TODAY}] SELF-CHAT CMD\n{entry}\n\n---\n"
    first_heading = text.find("\n## [")
    if first_heading == -1:
        updated = text + log_entry
    else:
        updated = text[:first_heading] + log_entry + text[first_heading:]
    LOG_FILE.write_text(updated, encoding="utf-8")

def find_action_line(text, action_id):
    """Find the line number and content of an open action."""
    lines = text.splitlines()
    pattern = re.compile(rf'\[{re.escape(action_id)}\]')
    for i, line in enumerate(lines):
        if pattern.search(line) and line.strip().startswith("- [ ]"):
            return i, line, lines
    return None, None, lines

def next_action_id(text):
    """Get the next available A-NNN id."""
    ids = [int(m) for m in re.findall(r'\[A-(\d+)\]', text)]
    return f"A-{max(ids) + 1}" if ids else "A-1"

# ─────────────────────────────────────────────
# DONE
# ─────────────────────────────────────────────
def cmd_done(args):
    if not args:
        return "Usage: done A-NNN [optional outcome]"

    action_id = args[0].upper()
    if not re.match(r'^A-\d+$', action_id):
        return f"❌ Invalid action ID: {action_id}. Format: A-123"

    outcome = " ".join(args[1:]) if len(args) > 1 else "Closed via WhatsApp self-chat"

    text = ACTIONS_FILE.read_text(encoding="utf-8")
    idx, line, lines = find_action_line(text, action_id)

    if idx is None:
        # Check if already closed
        for l in lines:
            if f"[{action_id}]" in l and "- [x]" in l:
                return f"ℹ️ [{action_id}] is already closed."
        return f"❌ [{action_id}] not found in open actions."

    # Extract short description
    desc_match = re.search(r'\*\*\[A-\d+\]\*\*\s*\*\*(.+?)\*\*', line)
    desc = desc_match.group(1).strip()[:60] if desc_match else action_id

    # Mark complete: replace - [ ] with - [x] and add outcome
    new_line = line.replace("- [ ]", "- [x]", 1)
    # Add resolved date and outcome after existing content
    if "[outcome::" not in new_line:
        new_line = new_line.rstrip() + f" ✅ {TODAY} [outcome::{outcome}]"

    lines[idx] = new_line
    ACTIONS_FILE.write_text("\n".join(lines), encoding="utf-8")
    append_log(f"- [{action_id}] marked complete via WhatsApp. Outcome: {outcome}")

    return f"✅ [{action_id}] done\n_{desc}_"

# ─────────────────────────────────────────────
# SNOOZE
# ─────────────────────────────────────────────
def cmd_snooze(args):
    if len(args) < 2:
        return "Usage: snooze A-NNN <days>"

    action_id = args[0].upper()
    try:
        days = int(args[1])
    except ValueError:
        return f"❌ Days must be a number, got: {args[1]}"

    text = ACTIONS_FILE.read_text(encoding="utf-8")
    idx, line, lines = find_action_line(text, action_id)

    if idx is None:
        return f"❌ [{action_id}] not found in open actions."

    new_date = (date.today() + timedelta(days=days)).isoformat()
    # Replace existing 📅 date or append if none
    if "📅" in line:
        new_line = re.sub(r'📅\s*\d{4}-\d{2}-\d{2}', f'📅 {new_date}', line)
    else:
        new_line = line.rstrip() + f" 📅 {new_date}"

    lines[idx] = new_line
    ACTIONS_FILE.write_text("\n".join(lines), encoding="utf-8")

    desc_match = re.search(r'\*\*\[A-\d+\]\*\*\s*\*\*(.+?)\*\*', line)
    desc = desc_match.group(1).strip()[:50] if desc_match else action_id

    return f"⏱ [{action_id}] snoozed {days}d → {new_date}\n_{desc}_"

# ─────────────────────────────────────────────
# ADD
# ─────────────────────────────────────────────
def cmd_add(args):
    if not args:
        return "Usage: add <description of action>"

    desc = " ".join(args)
    text = ACTIONS_FILE.read_text(encoding="utf-8")
    new_id = next_action_id(text)

    new_action = (
        f"\n- [ ] **[{new_id}]** **{desc}** "
        f"[owner::Fabio] [source::WhatsApp self-chat {TODAY}] 📅 {TODAY} 🔼\n"
    )

    # Insert before the first open action or at end of Open Items
    open_items_idx = text.find("## Open Items")
    if open_items_idx == -1:
        text += new_action
    else:
        # Find first action line after Open Items
        first_action = text.find("\n- ", open_items_idx)
        if first_action == -1:
            text += new_action
        else:
            text = text[:first_action] + new_action + text[first_action:]

    ACTIONS_FILE.write_text(text, encoding="utf-8")
    append_log(f"- [{new_id}] added via WhatsApp: {desc}")

    return f"➕ [{new_id}] added\n_{desc}_"

# ─────────────────────────────────────────────
# NOTE
# ─────────────────────────────────────────────
def cmd_note(args):
    if not args:
        return "Usage: note <your note text>"

    content = " ".join(args)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M ET")
    filename = f"whatsapp-note-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    filepath = RAW_DIR / filename

    RAW_DIR.mkdir(exist_ok=True)
    filepath.write_text(
        f"---\nsource: whatsapp-self-chat\ncaptured: {timestamp}\n---\n\n{content}\n",
        encoding="utf-8"
    )

    return f"📝 Captured\n_{content[:80]}_"

# ─────────────────────────────────────────────
# STATUS
# ─────────────────────────────────────────────
def cmd_status(args):
    if not args:
        return "Usage: status A-NNN"

    action_id = args[0].upper()
    text = ACTIONS_FILE.read_text(encoding="utf-8")
    pattern = re.compile(rf'\[{re.escape(action_id)}\]')

    for line in text.splitlines():
        if pattern.search(line):
            # Strip markdown formatting for WhatsApp
            clean = re.sub(r'\*+', '', line).strip()
            clean = re.sub(r'\[owner::[^\]]+\]', '', clean)
            clean = re.sub(r'\[source::[^\]]+\]', '', clean)
            clean = re.sub(r'\[contact::[^\]]+\]', '', clean)
            clean = re.sub(r'\s+', ' ', clean).strip()
            status_icon = "✅" if "- [x]" in line else "🔲"
            return f"{status_icon} {clean[:300]}"

    return f"❌ [{action_id}] not found."

# ─────────────────────────────────────────────
# FIND
# ─────────────────────────────────────────────
def cmd_find(args):
    if not args:
        return "Usage: find <search term>"

    query = " ".join(args).lower()
    results = []

    for md_file in VAULT.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            if query in content.lower():
                rel = md_file.relative_to(VAULT)
                # Find the matching line for context
                for line in content.splitlines():
                    if query in line.lower():
                        snippet = line.strip()[:60]
                        results.append(f"  {rel}: {snippet}")
                        break
        except:
            pass
        if len(results) >= 5:
            break

    if not results:
        return f"🔍 No results for '{query}'"
    return f"🔍 Found {len(results)} match{'es' if len(results)>1 else ''} for '{query}':\n" + "\n".join(results)

# ─────────────────────────────────────────────
# DISPATCH
# ─────────────────────────────────────────────
COMMANDS = {
    "done":   cmd_done,
    "snooze": cmd_snooze,
    "add":    cmd_add,
    "note":   cmd_note,
    "status": cmd_status,
    "find":   cmd_find,
}

def main():
    if len(sys.argv) < 2:
        print("Usage: vault-commands.py <command> [args...]")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    args = sys.argv[2:]

    handler = COMMANDS.get(cmd)
    if not handler:
        reply = f"❓ Unknown command: {cmd}\nTry: done, snooze, add, note, status, find"
    else:
        try:
            reply = handler(args)
        except Exception as e:
            reply = f"❌ Error: {e}"

    # Send reply via WhatsApp
    try:
        send_whatsapp(reply)
        print(f"Sent: {reply}")
    except Exception as e:
        print(f"WhatsApp error: {e}")
        print(f"Reply was: {reply}")

if __name__ == "__main__":
    main()
