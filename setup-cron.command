#!/bin/bash
# Installs a cron job to run price-monitor.py every 30 minutes
# Double-click this file to execute in Terminal

SCRIPT_DIR="$(dirname "$0")"
PYTHON=$(which python3 2>/dev/null || echo "/usr/local/bin/python3")
LOG="$SCRIPT_DIR/price-monitor.log"

# The cron line: every 30 minutes
# client_id is read from .seatgeek_client_id config file by price-monitor.py
CRON_LINE="*/30 * * * * $PYTHON $SCRIPT_DIR/price-monitor.py >> $LOG 2>&1"

echo "============================================"
echo "  FIFA WC Price Monitor — Cron Setup"
echo "============================================"
echo ""
echo "Will add this cron job:"
echo "  $CRON_LINE"
echo ""

# Check if already installed
if crontab -l 2>/dev/null | grep -q "price-monitor.py"; then
    echo "✓ Cron job already installed. Current crontab:"
    crontab -l | grep "price-monitor"
    echo ""
    echo "No changes made."
else
    # Add the cron line
    (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
    echo "✓ Cron job installed!"
    echo ""
    echo "Current crontab:"
    crontab -l
fi

echo ""
echo "To remove: run 'crontab -e' and delete the price-monitor line"
echo "Log file: $LOG"
echo ""
echo "--- Done. Press any key to close. ---"
read -n 1
