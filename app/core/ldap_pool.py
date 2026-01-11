"""
LDAP Connection Pool Manager
Manages LDAP connections dengan pooling dan retry mechanism
"""

import time
import threading
from queue import Queue, Empty
from ldap3 import Server, Connection, ALL
from app.config import LDAP_SERVER, LDAP_ADMIN_DN, LDAP_ADMIN_PASSWORD
from app.logger import logger


class LDAPConnectionPool:
    """
    LDAP Connection Pool dengan retry mechanism
    """
    def __init__(self, max_connections: int = 10, timeout: int = 5, max_retries: int = 3):
        self.max_connections = max_connections
        self.timeout = timeout
        self.max_retries = max_retries
        self.server = Server(LDAP_SERVER, get_info=ALL)
        
        # Separate pools untuk admin dan anonymous connections
        self.admin_pool = Queue(maxsize=max_connections)
        self.anon_pool = Queue(maxsize=max_connections)
        self.lock = threading.Lock()
        
        # Initialize pools
        self._initialize_pools()
    
    def _initialize_pools(self):
        """Initialize connection pools dengan beberapa connections"""
        # Initialize admin pool (2 connections)
        for _ in range(min(2, self.max_connections)):
            try:
                conn = self._create_admin_connection()
                self.admin_pool.put(conn)
            except Exception as e:
                logger.warning(f"Failed to initialize admin LDAP connection: {e}")
        
        # Initialize anonymous pool (3 connections)
        for _ in range(min(3, self.max_connections)):
            try:
                conn = self._create_anon_connection()
                self.anon_pool.put(conn)
            except Exception as e:
                logger.warning(f"Failed to initialize anonymous LDAP connection: {e}")
    
    def _create_admin_connection(self) -> Connection:
        """Create admin LDAP connection"""
        conn = Connection(
            self.server,
            user=LDAP_ADMIN_DN,
            password=LDAP_ADMIN_PASSWORD,
            auto_bind=True,
            receive_timeout=self.timeout
        )
        return conn
    
    def _create_anon_connection(self) -> Connection:
        """Create anonymous LDAP connection"""
        conn = Connection(
            self.server,
            auto_bind=True,
            receive_timeout=self.timeout
        )
        return conn
    
    def _is_connection_alive(self, conn: Connection) -> bool:
        """Check if connection is still alive"""
        try:
            if conn.bound:
                return True
        except:
            pass
        return False
    
    def _reconnect(self, conn: Connection, admin: bool = False) -> Connection:
        """Reconnect a dead connection"""
        try:
            if admin:
                return self._create_admin_connection()
            else:
                return self._create_anon_connection()
        except Exception as e:
            logger.error(f"Failed to reconnect LDAP: {e}")
            raise
    
    def get_connection(self, admin: bool = False, retry: bool = True) -> Connection:
        """
        Get connection from pool dengan retry mechanism
        Returns LDAP connection
        """
        pool = self.admin_pool if admin else self.anon_pool
        
        for attempt in range(self.max_retries if retry else 1):
            try:
                # Try to get connection from pool (non-blocking)
                try:
                    conn = pool.get_nowait()
                except Empty:
                    # Pool empty, create new connection
                    if admin:
                        conn = self._create_admin_connection()
                    else:
                        conn = self._create_anon_connection()
                
                # Check if connection is alive
                if self._is_connection_alive(conn):
                    return conn
                else:
                    # Connection dead, try to reconnect
                    logger.debug(f"LDAP connection dead, reconnecting...")
                    conn = self._reconnect(conn, admin)
                    return conn
                    
            except Exception as e:
                logger.warning(f"LDAP connection attempt {attempt + 1} failed: {e}")
                if attempt < (self.max_retries - 1):
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    raise
        
        raise Exception("Failed to get LDAP connection after retries")
    
    def return_connection(self, conn: Connection, admin: bool = False):
        """
        Return connection to pool
        """
        if conn is None:
            return
        
        pool = self.admin_pool if admin else self.anon_pool
        
        try:
            # Check if connection is still alive
            if self._is_connection_alive(conn):
                # Try to put back to pool (non-blocking)
                try:
                    pool.put_nowait(conn)
                except:
                    # Pool full, just close connection
                    conn.unbind()
            else:
                # Connection dead, don't return to pool
                try:
                    conn.unbind()
                except:
                    pass
        except Exception as e:
            logger.warning(f"Error returning LDAP connection to pool: {e}")
            try:
                conn.unbind()
            except:
                pass
    
    def close_all(self):
        """Close all connections in pools"""
        # Close admin pool
        while not self.admin_pool.empty():
            try:
                conn = self.admin_pool.get_nowait()
                conn.unbind()
            except:
                pass
        
        # Close anonymous pool
        while not self.anon_pool.empty():
            try:
                conn = self.anon_pool.get_nowait()
                conn.unbind()
            except:
                pass


# Global connection pool instance
_ldap_pool = None
_pool_lock = threading.Lock()


def get_ldap_pool() -> LDAPConnectionPool:
    """Get global LDAP connection pool instance"""
    global _ldap_pool
    if _ldap_pool is None:
        with _pool_lock:
            if _ldap_pool is None:
                _ldap_pool = LDAPConnectionPool(
                    max_connections=10,
                    timeout=5,
                    max_retries=3
                )
    return _ldap_pool


def close_ldap_pool():
    """Close global LDAP connection pool"""
    global _ldap_pool
    if _ldap_pool:
        _ldap_pool.close_all()
        _ldap_pool = None
