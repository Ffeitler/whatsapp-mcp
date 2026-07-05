#!/usr/bin/env python3
"""
WC Ticket Price Monitor — Ticketmaster edition
Polls the Jul 11 Miami WC Quarterfinal on Ticketmaster,
sends WhatsApp self-chat alerts when price changes.

Setup:
  1. Get a free API key at https://developer.ticketmaster.com
  2. Save it to ~/Desktop/whatsapp-mcp/.ticketmaster_api_key
  3. Run install-launchagent.command to schedule every 30 min
"""

import json, os, urllib.request, urllib.parse
from datetime import datetime

# --- Config ---
STATE_FILE   = os.path.expanduser("~/Desktop/whatsapp-mcp/.price-monitor-state.json")
BRIDGE_URL   = "http://localhost:8080/api/send"
SELF_CHAT_JID = "211626041049100@lid"
ALWAYS_SEND  = os.environ.get("ALWAYS_SEND", "0") == "1"

# Ticketmaster event ID for Jul 11 WC QF Miami — update if wrong
TM_EVENT_ID  = os.environ.get("TM_EVENT_ID", "")

# Ticketmaster API key — load from file or env
def load_tm_key():
    env_key = os.environ.get("TM_API_KEY", "")
    if env_key:
        return env_key
    key_file = os.path.expanduser("~/Desktop/whatsapp-mcp/.ticketmaster_api_key")
    if os.path.exists(key_file):
        return open(key_file).read().strip()
    return ""

def search_wc_miami_event(api_key):
    """Search Ticketmaster for WC Miami events to find the correct event ID."""
    params = urllib.parse.urlencode({
        "keyword": "FIFA World Cup",
        "stateCode": "FL",
        "size": "20",
        "sort": "date,asc",
        "apikey": api_key,
    })
    url = f"https://app.ticketmaster.com/discovery/v2/events.json?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    events = data.get("_embedded", {}).get("events", [])
    # Filter for Miami / Hard Rock Stadium
    miami_events = []
    for e in events:
        venues = e.get("_embedded", {}).get("venues", [{}])
        city = venues[0].get("city", {}).get("name", "")
        name = e.get("name", "")
        if "miami" in city.lower() or "hard rock" in str(venues[0]).lower():
            miami_events.append(e)
    return events, miami_events

def fetch_tm_event_prices(event_id, api_key):
    """Fetch price ranges for a specific Ticketmaster event."""
    params = urllib.parse.urlencode({"apikey": api_key})
    url = f"https://app.ticketmaster.com/discovery/v2/events/{event_id}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    prices = data.get("priceRanges", [])
    event_url = data.get("url", "")
    event_name = data.get("name", "")
    date = data.get("dates", {}).get("start", {}).get("localDate", "")
    if prices:
        min_p = prices[0].get("min")
        max_p = prices[0].get("max")
        return min_p, max_p, event_url, event_name, date
    return None, None, event_url, event_name, date

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            return json.load(open(STATE_FILE))
        except:
            pass
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def send_whatsapp(msg):
    payload = json.dumps({"recipient": SELF_CHAT_JID, "message": msg}).encode()
    req = urllib.request.Request(
        BRIDGE_URL, data=payload,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status

def main():
    api_key = load_tm_key()
    if not api_key:
        print("ERROR: No Ticketmaster API key found.")
        print("Get a free key at https://developer.ticketmaster.com")
        print("Save it to ~/Desktop/whatsapp-mcp/.ticketmaster_api_key")
        return

    event_id = TM_EVENT_ID
    state = load_state()

    # If no event ID, search for the Miami WC game
    if not event_id:
        event_id = state.get("tm_event_id", "")

    if not event_id:
        print("Searching Ticketmaster for WC Miami events...")
        try:
            all_events, miami_events = search_wc_miami_event(api_key)
            if miami_events:
                print(f"Found {len(miami_events)} Miami WC events:")
                for e in miami_events:
                    dates = e.get("dates", {}).get("start", {})
                    print(f"  ID={e['id']} | {e['name']} | {dates.get('localDate')} | {e.get('url','')}")
                # Auto-pick the July 11 one
                for e in miami_events:
                    date = e.get("dates", {}).get("start", {}).get("localDate", "")
                    if "2026-07-11" in date or "Jul 11" in e.get("name", ""):
                        event_id = e["id"]
                        print(f"Auto-selected: {e['name']} ({event_id})")
                        break
                if not event_id and miami_events:
                    event_id = miami_events[0]["id"]
                    print(f"Using first Miami event: {miami_events[0]['name']} ({event_id})")
            else:
                print(f"No Miami events found. All FL events ({len(all_events)}):")
                for e in all_events[:5]:
                    dates = e.get("dates", {}).get("start", {})
                    venues = e.get("_embedded", {}).get("venues", [{}])
                    city = venues[0].get("city", {}).get("name", "")
                    print(f"  ID={e['id']} | {e['name']} | {dates.get('localDate')} | {city}")
                return
        except Exception as ex:
            print(f"Search failed: {ex}")
            return

    # Fetch prices for the event
    try:
        min_p, max_p, url, name, date = fetch_tm_event_prices(event_id, api_key)
    except Exception as ex:
        print(f"Price fetch failed for event {event_id}: {ex}")
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M ET")
    print(f"Event: {name} ({date})")
    print(f"Prices: ${min_p} – ${max_p}")
    print(f"URL: {url}")

    prev_min = state.get("min_price")
    prev_max = state.get("max_price")
    changed = (min_p != prev_min or max_p != prev_max)

    if changed or ALWAYS_SEND:
        delta = ""
        if prev_min is not None and min_p is not None:
            diff = min_p - prev_min
            delta = f" ({'↑' if diff > 0 else '↓'}${abs(diff):.0f})"
        msg = (
            f"🎟️ WC QF Miami — Hard Rock Stadium ({date})\n"
            f"Min: ${min_p}{delta} | Max: ${max_p}\n"
            f"🔗 {url}\n"
            f"⏱ {now}"
        )
        try:
            status = send_whatsapp(msg)
            print(f"WhatsApp sent (status {status})")
        except Exception as ex:
            print(f"WhatsApp failed: {ex}")

        state.update({
            "min_price": min_p,
            "max_price": max_p,
            "last_check": now,
            "tm_event_id": event_id,
        })
        save_state(state)
    else:
        print(f"No change (prev: ${prev_min}–${prev_max}). No alert sent.")
        state["last_check"] = now
        save_state(state)

if __name__ == "__main__":
    main()
