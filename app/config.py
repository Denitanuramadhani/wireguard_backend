# ======================
# LDAP CONFIG
# ======================
LDAP_SERVER = "ldap://117.53.44.59:389"
LDAP_BASE_DN = "dc=example,dc=com"
LDAP_USER_DN = "uid={},ou=people,dc=example,dc=com"

# ======================
# WIREGUARD CONFIG
# ======================
WG_INTERFACE = "wg0"
WG_CONF_PATH = "/etc/wireguard/wg0.conf"
WG_SERVER_PUBLIC_KEY = "w+JEv1CDgtrOduepTLLW90rekFgHwvKoJTBsPEBOXDo="
WG_ENDPOINT = "117.53.44.59:51820" 

JWT_SECRET = "6fa6969e55e9b8d5fce4e1117fe1f95ee42e47f50dd6d5dc781a9423e70b3e7f"
JWT_ALGO = "HS256"