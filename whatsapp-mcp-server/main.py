from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
from whatsapp import (
    search_contacts as whatsapp_search_contacts,
    list_messages as whatsapp_list_messages,
    list_chats as whatsapp_list_chats,
    get_chat as whatsapp_get_chat,
    get_direct_chat_by_contact as whatsapp_get_direct_chat_by_contact,
    get_contact_chats as whatsapp_get_contact_chats,
    get_last_interaction as whatsapp_get_last_interaction,
    get_message_context as whatsapp_get_message_context,
    send_message as whatsapp_send_message,
    send_file as whatsapp_send_file,
    send_audio_message as whatsapp_audio_voice_message,
    download_media as whatsapp_download_media
)

# Initialize FastMCP server
mcp = FastMCP("whatsapp")

@mcp.tool()
def search_contacts(query: str) -> List[Dict[str, Any]]:
    """Search WhatsApp contacts by name or phone number.
    
    Args:
        query: Search term to match against contact names or phone numbers
    """
    contacts = whatsapp_search_contacts(query)
    return contacts

@mcp.tool()
def list_messages(
    after: Optional[str] = None,
    before: Optional[str] = None,
    sender_phone_number: Optional[str] = None,
    chat_jid: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_context: bool = True,
    context_before: int = 1,
    context_after: int = 1
) -> List[Dict[str, Any]]:
    """Get WhatsApp messages matching specified criteria with optional context.
    
    Args:
        after: Optional ISO-8601 formatted string to only return messages after this date
        before: Optional ISO-8601 formatted string to only return messages before this date
        sender_phone_number: Optional phone number to filter messages by sender
        chat_jid: Optional chat JID to filter messages by chat
        query: Optional search term to filter messages by content
        limit: Maximum number of messages to return (default 20)
        page: Page number for pagination (default 0)
        include_context: Whether to include messages before and after matches (default True)
        context_before: Number of messages to include before each match (default 1)
        context_after: Number of messages to include after each match (default 1)
    """
    messages = whatsapp_list_messages(
        after=after,
        before=before,
        sender_phone_number=sender_phone_number,
        chat_jid=chat_jid,
        query=query,
        limit=limit,
        page=page,
        include_context=include_context,
        context_before=context_before,
        context_after=context_after
    )
    return messages

@mcp.tool()
def list_chats(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_last_message: bool = True,
    sort_by: str = "last_active"
) -> List[Dict[str, Any]]:
    """Get WhatsApp chats matching specified criteria.
    
    Args:
        query: Optional search term to filter chats by name or JID
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
        include_last_message: Whether to include the last message in each chat (default True)
        sort_by: Field to sort results by, either "last_active" or "name" (default "last_active")
    """
    chats = whatsapp_list_chats(
        query=query,
        limit=limit,
        page=page,
        include_last_message=include_last_message,
        sort_by=sort_by
    )
    return chats

@mcp.tool()
def get_chat(chat_jid: str, include_last_message: bool = True) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by JID.
    
    Args:
        chat_jid: The JID of the chat to retrieve
        include_last_message: Whether to include the last message (default True)
    """
    chat = whatsapp_get_chat(chat_jid, include_last_message)
    return chat

@mcp.tool()
def get_direct_chat_by_contact(sender_phone_number: str) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by sender phone number.
    
    Args:
        sender_phone_number: The phone number to search for
    """
    chat = whatsapp_get_direct_chat_by_contact(sender_phone_number)
    return chat

@mcp.tool()
def get_contact_chats(jid: str, limit: int = 20, page: int = 0) -> List[Dict[str, Any]]:
    """Get all WhatsApp chats involving the contact.
    
    Args:
        jid: The contact's JID to search for
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
    """
    chats = whatsapp_get_contact_chats(jid, limit, page)
    return chats

@mcp.tool()
def get_last_interaction(jid: str) -> str:
    """Get most recent WhatsApp message involving the contact.
    
    Args:
        jid: The JID of the contact to search for
    """
    message = whatsapp_get_last_interaction(jid)
    return message

@mcp.tool()
def get_message_context(
    message_id: str,
    before: int = 5,
    after: int = 5
) -> Dict[str, Any]:
    """Get context around a specific WhatsApp message.
    
    Args:
        message_id: The ID of the message to get context for
        before: Number of messages to include before the target message (default 5)
        after: Number of messages to include after the target message (default 5)
    """
    context = whatsapp_get_message_context(message_id, before, after)
    return context

@mcp.tool()
def send_message(
    recipient: str,
    message: str
) -> Dict[str, Any]:
    """Send a WhatsApp message to a person or group. For group chats use the JID.

    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        message: The message text to send
    
    Returns:
        A dictionary containing success status and a status message
    """
    # Validate input
    if not recipient:
        return {
            "success": False,
            "message": "Recipient must be provided"
        }
    
    # Call the whatsapp_send_message function with the unified recipient parameter
    success, status_message = whatsapp_send_message(recipient, message)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def send_file(recipient: str, media_path: str) -> Dict[str, Any]:
    """Send a file such as a picture, raw audio, video or document via WhatsApp to the specified recipient. For group messages use the JID.
    
    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        media_path: The absolute path to the media file to send (image, video, document)
    
    Returns:
        A dictionary containing success status and a status message
    """
    
    # Call the whatsapp_send_file function
    success, status_message = whatsapp_send_file(recipient, media_path)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def send_audio_message(recipient: str, media_path: str) -> Dict[str, Any]:
    """Send any audio file as a WhatsApp audio message to the specified recipient. For group messages use the JID. If it errors due to ffmpeg not being installed, use send_file instead.
    
    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        media_path: The absolute path to the audio file to send (will be converted to Opus .ogg if it's not a .ogg file)
    
    Returns:
        A dictionary containing success status and a status message
    """
    success, status_message = whatsapp_audio_voice_message(recipient, media_path)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def download_media(message_id: str, chat_jid: str) -> Dict[str, Any]:
    """Download media from a WhatsApp message and get the local file path.
    
    Args:
        message_id: The ID of the message containing the media
        chat_jid: The JID of the chat containing the message
    
    Returns:
        A dictionary containing success status, a status message, and the file path if successful
    """
    file_path = whatsapp_download_media(message_id, chat_jid)
    
    if file_path:
        return {
            "success": True,
            "message": "Media downloaded successfully",
            "file_path": file_path
        }
    else:
        return {
            "success": False,
            "message": "Failed to download media"
        }

# 2026-08-02: Google Maps directions, added here (not a new MCP server) to reuse
# this already-configured stdio server rather than stand up a second one just
# for one read-only tool. Key from GOOGLE_MAPS_API_KEY, inherited from whatever
# launched the parent `claude` process (wa-bot.sh sources config/secondbrain.local.env
# via lib/common.sh before invoking claude — see secondbrain-automation repo).
@mcp.tool()
def get_directions(origin: str, destination: str) -> Dict[str, Any]:
    """Get real driving directions (live distance, duration, and route summary) between two places via the Google Maps Directions API.

    Args:
        origin: Starting point — an address, place name, or "lat,lng"
        destination: Destination — an address, place name, or "lat,lng"

    Returns:
        A dictionary with success status, and on success: distance, duration,
        resolved start/end addresses, and a short list of major route steps
        (street names only, not full turn-by-turn — keep replies concise).
    """
    import os
    import urllib.parse
    import urllib.request
    import json as _json
    import re

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"success": False, "message": "GOOGLE_MAPS_API_KEY not set in environment"}

    params = urllib.parse.urlencode({"origin": origin, "destination": destination, "key": api_key})
    url = f"https://maps.googleapis.com/maps/api/directions/json?{params}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = _json.loads(resp.read())
    except Exception as e:
        return {"success": False, "message": f"Directions API request failed: {e}"}

    status = data.get("status")
    if status != "OK":
        return {"success": False, "message": f"Directions API status={status}: {data.get('error_message', '')}"}

    route = data["routes"][0]
    leg = route["legs"][0]
    # Strip HTML tags from step instructions (API returns e.g. "Head <b>north</b>").
    steps = [re.sub("<[^<]+?>", "", s["html_instructions"]) for s in leg["steps"]]

    return {
        "success": True,
        "distance": leg["distance"]["text"],
        "duration": leg["duration"]["text"],
        "start_address": leg["start_address"],
        "end_address": leg["end_address"],
        "major_steps": steps[:6],
    }

# Ride links — Uber has no consumer ride-request API (the Rides API "request"
# scope was closed to new apps), so "get me an uber" ends in a one-tap deep link
# that opens the Uber app with the dropoff filled in and pickup = the phone's own
# GPS; Fabio taps Request himself. The link is built here, not by the model, so
# coordinates and URL-encoding are never hand-typed.
@mcp.tool()
def get_ride_link(destination: str, origin: str = "") -> Dict[str, Any]:
    """Build one-tap Uber (and Lyft) links that open the app with the destination pre-filled.

    Pickup is always the phone's current GPS location (set in the app), so this never
    guesses where Fabio is standing. Nothing is booked — he confirms in the app.

    Args:
        destination: Where to go — an address, place name, or "lat,lng"
        origin: Optional best-known current location, used only to estimate trip
            distance/duration (driving). Leave empty if unknown.

    Returns:
        success, uber_link, lyft_link, resolved destination address + lat/lng, and
        (when origin was given) the driving distance/duration estimate.
    """
    import os
    import urllib.parse
    import urllib.request
    import json as _json

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"success": False, "message": "GOOGLE_MAPS_API_KEY not set in environment"}

    def _get(url: str) -> Dict[str, Any]:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return _json.loads(resp.read())

    trip: Dict[str, Any] = {}
    try:
        if origin:
            params = urllib.parse.urlencode({"origin": origin, "destination": destination, "key": api_key})
            data = _get(f"https://maps.googleapis.com/maps/api/directions/json?{params}")
            if data.get("status") != "OK":
                return {"success": False, "message": f"Directions API status={data.get('status')}: {data.get('error_message', '')}"}
            leg = data["routes"][0]["legs"][0]
            loc, address = leg["end_location"], leg["end_address"]
            trip = {"distance": leg["distance"]["text"], "duration": leg["duration"]["text"]}
        else:
            params = urllib.parse.urlencode({"address": destination, "key": api_key})
            data = _get(f"https://maps.googleapis.com/maps/api/geocode/json?{params}")
            if data.get("status") != "OK":
                return {"success": False, "message": f"Geocoding API status={data.get('status')}: {data.get('error_message', '')}"}
            result = data["results"][0]
            loc, address = result["geometry"]["location"], result["formatted_address"]
    except Exception as e:
        return {"success": False, "message": f"Maps API request failed: {e}"}

    lat, lng = loc["lat"], loc["lng"]
    uber = "https://m.uber.com/ul/?" + urllib.parse.urlencode({
        "action": "setPickup",
        "pickup": "my_location",
        "dropoff[latitude]": lat,
        "dropoff[longitude]": lng,
        "dropoff[nickname]": destination,
        "dropoff[formatted_address]": address,
    })
    lyft = "https://lyft.com/ride?" + urllib.parse.urlencode({
        "id": "lyft",
        "destination[latitude]": lat,
        "destination[longitude]": lng,
    })
    return {
        "success": True,
        "uber_link": uber,
        "lyft_link": lyft,
        "destination_address": address,
        "destination_lat": lat,
        "destination_lng": lng,
        **trip,
    }

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')