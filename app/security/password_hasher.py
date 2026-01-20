import subprocess
import hashlib
import os
import base64
from app.logger import logger


class PasswordHashError(Exception):
    pass


def hash_with_slappasswd(password: str) -> str:
    """
    Hash password menggunakan slappasswd (Linux only)
    """
    try:
        output = subprocess.check_output(
            ["slappasswd", "-s", password],
            stderr=subprocess.STDOUT
        )
        return output.decode().strip()
    except FileNotFoundError:
        raise PasswordHashError("slappasswd not found on this system")
    except subprocess.CalledProcessError as e:
        raise PasswordHashError(
            f"slappasswd failed: {e.output.decode().strip()}"
        )


def hash_with_python_ssha(password: str) -> str:
    """
    Hash password SSHA murni Python (cross-platform)
    Compatible dengan OpenLDAP
    """
    salt = os.urandom(4)
    sha1 = hashlib.sha1(password.encode("utf-8") + salt).digest()
    ssha = base64.b64encode(sha1 + salt).decode("utf-8")
    return "{SSHA}" + ssha


def hash_password(password: str, mode: str = "auto") -> str:
    """
    mode:
      - auto        : try slappasswd, fallback ke python SSHA
      - slappasswd  : force slappasswd
      - python      : force python SSHA
    """
    logger.debug(f"[HASH] Password hashing mode: {mode}")

    if mode == "python":
        logger.info("[HASH] Using Python SSHA hasher")
        return hash_with_python_ssha(password)

    if mode == "slappasswd":
        logger.info("[HASH] Using slappasswd hasher")
        return hash_with_slappasswd(password)

    # auto mode
    try:
        logger.info("[HASH] Trying slappasswd hasher (auto mode)")
        return hash_with_slappasswd(password)
    except PasswordHashError as e:
        logger.warning(f"[HASH] {e}, fallback to Python SSHA")
        return hash_with_python_ssha(password)