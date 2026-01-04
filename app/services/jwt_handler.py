from jose import jwt
from datetime import datetime, timedelta
from app.config import JWT_SECRET, JWT_ALGO

def create_token(data: dict):
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=12)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

def verify_token(token: str):
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])