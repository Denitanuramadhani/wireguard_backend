from ldap3 import Server, Connection, ALL
from ldap3.core.exceptions import (
    LDAPException, LDAPSocketOpenError, LDAPBindError,
    LDAPInvalidCredentialsResult, LDAPInvalidDnError
)
from app.config import LDAP_SERVER, LDAP_USER_DN
from app.logger import logger

def ldap_authenticate(username: str, password: str) -> bool:
    """
    Authenticate user dengan LDAP
    Returns True jika credentials valid, False jika invalid
    Raises Exception jika terjadi error yang tidak expected (untuk handling di caller)
    
    Note: Tidak check wireguardEnabled di sini, check dilakukan setelah login
    """
    # #region agent log
    import json
    import time
    try:
        with open(r'c:\wireguard_backend\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"ldap_auth.py:8","message":"ldap_authenticate called","data":{"username":username,"has_password":bool(password)},"timestamp":int(time.time()*1000)}) + '\n')
    except: pass
    # #endregion
    
    if not username or not password:
        logger.warning(f"[LDAP AUTH] Missing username or password")
        return False
    
    conn = None
    try:
        # Create server connection
        # #region agent log
        try:
            with open(r'c:\wireguard_backend\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"ldap_auth.py:25","message":"Before Server creation","data":{"ldap_server":LDAP_SERVER},"timestamp":int(time.time()*1000)}) + '\n')
        except: pass
        # #endregion
        
        try:
            server = Server(LDAP_SERVER, get_info=ALL)
            logger.debug(f"[LDAP AUTH] Connecting to server: {LDAP_SERVER}")
            # #region agent log
            try:
                with open(r'c:\wireguard_backend\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"ldap_auth.py:30","message":"Server created","data":{},"timestamp":int(time.time()*1000)}) + '\n')
            except: pass
            # #endregion
        except Exception as e:
            # #region agent log
            try:
                with open(r'c:\wireguard_backend\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"ldap_auth.py:35","message":"Server creation exception","data":{"error_type":type(e).__name__,"error_msg":str(e)},"timestamp":int(time.time()*1000)}) + '\n')
            except: pass
            # #endregion
            logger.error(
                f"[LDAP AUTH ERROR] Failed to create server object for {username}: {e}",
                exc_info=True
            )
            raise  # Re-raise untuk handling di caller
        
        # Format user DN
        try:
            user_dn = LDAP_USER_DN.format(username)
            logger.debug(f"[LDAP AUTH] User DN: {user_dn}")
        except Exception as e:
            logger.error(
                f"[LDAP AUTH ERROR] Failed to format user DN for {username}: {e}",
                exc_info=True
            )
            raise  # Re-raise untuk handling di caller
        
        # Attempt bind
        # #region agent log
        try:
            with open(r'c:\wireguard_backend\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"ldap_auth.py:50","message":"Before Connection bind","data":{"user_dn":user_dn},"timestamp":int(time.time()*1000)}) + '\n')
        except: pass
        # #endregion
        
        try:
            conn = Connection(
                server,
                user=user_dn,
                password=password,
                auto_bind=True
            )
            
            # #region agent log
            try:
                with open(r'c:\wireguard_backend\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"ldap_auth.py:60","message":"After Connection bind","data":{"bound":conn.bound if conn else False},"timestamp":int(time.time()*1000)}) + '\n')
            except: pass
            # #endregion
            
            # Verify bind was successful
            if conn.bound:
                logger.info(f"[LDAP AUTH SUCCESS] User {username} authenticated successfully")
                return True
            else:
                logger.warning(f"[LDAP AUTH] Bind completed but connection not bound for {username}")
                return False
                
        except LDAPInvalidCredentialsResult as e:
            # Invalid credentials - ini expected, return False (bukan error)
            logger.debug(f"[LDAP AUTH] Invalid credentials for {username}: {e}")
            return False
            
        except LDAPBindError as e:
            # Bind error - bisa invalid credentials atau server error
            error_code = e.result.get('result', -1) if hasattr(e, 'result') else -1
            
            # Error code 49 = Invalid credentials
            if error_code == 49:
                logger.debug(f"[LDAP AUTH] Invalid credentials for {username} (error code: {error_code})")
                return False
            else:
                # Other bind errors - re-raise untuk handling di caller
                logger.error(
                    f"[LDAP AUTH ERROR] LDAP bind error for {username} (error code: {error_code}): {e}",
                    exc_info=True
                )
                raise
                
        except LDAPInvalidDnError as e:
            # Invalid DN format - re-raise untuk handling di caller
            logger.error(
                f"[LDAP AUTH ERROR] Invalid DN format for {username}: {e}",
                exc_info=True
            )
            raise
            
        except LDAPSocketOpenError as e:
            # Connection error - re-raise untuk handling di caller
            logger.error(
                f"[LDAP AUTH ERROR] Failed to connect to LDAP server for {username}: {e}",
                exc_info=True
            )
            raise
            
        except LDAPException as e:
            # Other LDAP errors - re-raise untuk handling di caller
            logger.error(
                f"[LDAP AUTH ERROR] LDAP exception for {username}: {type(e).__name__}: {e}",
                exc_info=True
            )
            if hasattr(e, 'result'):
                logger.error(f"[LDAP AUTH ERROR] LDAP result: {e.result}")
            raise
            
    except (LDAPException, Exception) as e:
        # Re-raise untuk handling di caller (bukan return False)
        # Caller akan handle error ini dengan HTTPException yang sesuai
        logger.error(
            f"[LDAP AUTH CRITICAL ERROR] Unexpected error authenticating {username}: {e}",
            exc_info=True
        )
        raise
        
    finally:
        # Cleanup connection
        if conn:
            try:
                conn.unbind()
            except Exception as e:
                logger.warning(f"[LDAP AUTH] Error during connection cleanup: {e}")
