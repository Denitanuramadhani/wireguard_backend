from ldap3 import Server, Connection, ALL
from app.config import LDAP_SERVER, LDAP_USER_DN
from app.logger import logger

def ldap_authenticate(username: str, password: str) -> bool:
    """
    Authenticate user dengan LDAP
    Returns True jika credentials valid
    Note: Tidak check wireguardEnabled di sini, check dilakukan setelah login
    """
    try:
        server = Server(LDAP_SERVER, get_info=ALL)

        user_dn = LDAP_USER_DN.format(username)

        conn = Connection(
            server,
            user=user_dn,
            password=password,
            auto_bind=True
        )

        return True

    except Exception as e:
        logger.error(f"[LDAP AUTH ERROR] {username}: {e}")
        return False
