#!/bin/bash
echo "Menghentikan Health Agency Studio..."

# Matikan proses python server yang memakai port 8000
PID=$(lsof -ti:8000)
if [ ! -z "$PID" ]; then
    kill -9 $PID
    echo "✓ Server di port 8000 (PID: $PID) berhasil dimatikan."
else
    # Fallback dengan pkill
    pkill -f "python3 server.py" 2>/dev/null
    echo "✓ Server Health Studio telah dimatikan."
fi

sleep 1
