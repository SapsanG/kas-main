#!/bin/bash

# Path to Python and the main bot file
PYTHON_PATH=python
SCRIPT_DIR=$(dirname "$0")
BOT_SCRIPT="$SCRIPT_DIR/app/main.py"

# Log file for events
LOG_FILE="$SCRIPT_DIR/logs/bot_restart_log.txt"

# Create logs directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/logs"

while true; do
    echo "[$(date)] Starting bot..." >> "$LOG_FILE"
    $PYTHON_PATH "$BOT_SCRIPT"

    # Check exit code
    if [ $? -ne 0 ]; then
        echo "[$(date)] Bot terminated with an error. Restarting in 5 seconds..." >> "$LOG_FILE"
        sleep 5
        continue
    else
        echo "[$(date)] Bot terminated normally." >> "$LOG_FILE"
        break
    fi
done

# Keep terminal open (equivalent to pause in Windows)
read -p "Press Enter to continue..."