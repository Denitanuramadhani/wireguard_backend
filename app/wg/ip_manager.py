import json
import os

IP_FILE = "allocated_ips.json"

# Range IP WireGuard
NETWORK_PREFIX = "10.8.0."
START_IP = 2
END_IP = 250

# Buat file kalau belum ada
if not os.path.exists(IP_FILE):
    with open(IP_FILE, "w") as f:
        json.dump({}, f)

def load_ips():
    with open(IP_FILE, "r") as f:
        return json.load(f)

def save_ips(data):
    with open(IP_FILE, "w") as f:
        json.dump(data, f, indent=4)

def allocate_ip(username):
    data = load_ips()

    # Kalau user sudah punya IP → pakai IP sebelumnya
    if username in data:
        return data[username]

    # Cari IP baru
    for i in range(START_IP, END_IP):
        candidate = NETWORK_PREFIX + str(i)
        if candidate not in data.values():
            data[username] = candidate
            save_ips(data)
            return candidate

    raise Exception("No IP available in WireGuard pool")