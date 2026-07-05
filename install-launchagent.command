#!/bin/bash
# Installs the LaunchAgent (macOS-native scheduler, runs every 30 min)
# Double-click to execute

PLIST_SRC="$(dirname "$0")/com.fabio.price-monitor.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.fabio.price-monitor.plist"

echo "============================================"
echo "  FIFA WC Price Monitor — LaunchAgent Setup"
echo "============================================"
echo ""

# Copy plist to LaunchAgents
cp "$PLIST_SRC" "$PLIST_DEST"
echo "✓ Copied plist to ~/Library/LaunchAgents/"

# Unload any existing version first
launchctl unload "$PLIST_DEST" 2>/dev/null

# Load and start
launchctl load "$PLIST_DEST"
echo "✓ LaunchAgent loaded — runs every 30 minutes, starting now"
echo ""
echo "Useful commands:"
echo "  Stop:    launchctl unload ~/Library/LaunchAgents/com.fabio.price-monitor.plist"
echo "  Restart: launchctl unload ... && launchctl load ..."
echo "  Log:     tail -f ~/Desktop/whatsapp-mcp/price-monitor.log"
echo ""
echo "--- Done. Press any key to close. ---"
read -n 1
