#!/bin/bash
# Pindah ke direktori skrip ini berada
cd "$(dirname "$0")"

# Cek apakah virtual environment ada
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Cek apakah server sudah berjalan sebelumnya di port 8000
PID=$(lsof -ti:8000)
if [ ! -z "$PID" ]; then
    echo "Server sudah berjalan di port 8000 (PID: $PID). Membuka browser..."
    open http://localhost:8000
    exit 0
fi

# Jalankan server di background
nohup python3 server.py > server.log 2>&1 &

# Tunggu 1.5 detik agar server siap
sleep 1.5

# Buka langsung di browser Chrome/Safari bawaan Mac
open http://localhost:8000

echo "✓ Health Agency Studio berhasil dijalankan di background!"
echo "👉 Anda bisa langsung menutup jendela ini kapan saja."
