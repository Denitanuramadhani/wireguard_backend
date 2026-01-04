from fastapi import APIRouter
import os
import re
from datetime import datetime

router = APIRouter(prefix="/wg", tags=["WireGuard"])

BASE_DIR = "generated_configs"

@router.get("/users")
def list_users():
    users = []

    if not os.path.exists(BASE_DIR):
        return []

    for filename in os.listdir(BASE_DIR):
        if not filename.endswith(".conf"):
            continue

        username = filename.replace(".conf", "")
        path = f"{BASE_DIR}/{filename}"

        # Baca isi file
        with open(path, "r") as f:
            content = f.read()

        # Regex untuk tarik public key & address
#        pub = re.search(r"PublicKey\s*=\s*(.*)", content)
        pub = re.search(r"# ClientPublicKey = (.*)", content)
        addr = re.search(r"Address\s*=\s*([\d\.]+)/", content)

        users.append({
            "username": username,
            "address": addr.group(1) if addr else None,
            "public_key": pub.group(1) if pub else None,
            "updated_at": datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
        })

    return users
