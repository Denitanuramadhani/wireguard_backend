from ldap3 import Server, Connection, ALL
from app.config import LDAP_SERVER, LDAP_USER_DN

def ldap_authenticate(username: str, password: str):
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
        print("[LDAP ERROR] ->", e)
        return False
