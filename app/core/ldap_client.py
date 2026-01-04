#from ldap3 import Server, Connection, ALL
#from app.config import LDAP_SERVER, LDAP_BASE_DN
#
#def ldap_login(username, password):
#    try:
#        server = Server(LDAP_SERVER, get_info=ALL)
#        user_dn = f"uid={username},{LDAP_BASE_DN}"
#        conn = Connection(server, user=user_dn, password=password)
#       return conn.bind()
#    except:
#        return False
#def ldap_login(username, password):
    # MODE DUMMY UNTUK TESTING
#    if username == "denita" and password == "123":
#        return True
#    return False
