#!/bin/bash
# Test the FIFA WC price monitor — runs once with ALWAYS_SEND=1
# Double-click this file to execute in Terminal

cd "$(dirname "$0")"

echo "============================================"
echo "  FIFA WC QF Miami — Price Monitor Test"
echo "============================================"
echo ""

# Try python3 from common locations
PYTHON=$(which python3 2>/dev/null || echo "/usr/local/bin/python3")

echo "Using Python: $PYTHON"
echo ""

# First check if requests is installed
"$PYTHON" -c "import requests" 2>/dev/null || {
    echo "Installing requests..."
    "$PYTHON" -m pip install requests --quiet
}

echo "--- Running monitor (ALWAYS_SEND=1) ---"
echo ""
ALWAYS_SEND=1 "$PYTHON" "$(dirname "$0")/price-monitor.py"

echo ""
echo "--- Done. Press any key to close. ---"
read -n 1
