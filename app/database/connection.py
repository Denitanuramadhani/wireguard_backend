"""
MySQL Database Connection Pool
Handles connection pooling and database operations
"""

import pymysql
from pymysql import Error
from contextlib import contextmanager
from app.config import (
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DATABASE,
    MYSQL_POOL_SIZE,
    MYSQL_MAX_OVERFLOW,
    MYSQL_CONNECT_TIMEOUT
)
from app.logger import logger

# Connection pool (simple implementation)
_pool = []
_pool_size = MYSQL_POOL_SIZE
_max_overflow = MYSQL_MAX_OVERFLOW


def _create_connection():
    """Create a new MySQL connection (remote connection)"""
    try:
        connection = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
            connect_timeout=MYSQL_CONNECT_TIMEOUT,
            read_timeout=30,  # Timeout untuk read operations
            write_timeout=30  # Timeout untuk write operations
        )
        logger.debug(f"MySQL connection created to {MYSQL_HOST}:{MYSQL_PORT}")
        return connection
    except Error as e:
        logger.error(f"Error creating MySQL connection to {MYSQL_HOST}:{MYSQL_PORT}: {e}")
        raise


@contextmanager
def get_db_connection():
    """
    Get database connection from pool (context manager)
    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ...")
            result = cursor.fetchall()
    """
    connection = None
    try:
        # Try to get connection from pool
        if _pool:
            connection = _pool.pop()
            # Test if connection is still alive
            try:
                connection.ping(reconnect=False)
            except:
                # Connection is dead, create new one
                connection = _create_connection()
        else:
            # Pool is empty, create new connection
            connection = _create_connection()
        
        yield connection
        
        # Return connection to pool if pool is not full
        if len(_pool) < _pool_size:
            _pool.append(connection)
        else:
            connection.close()
            
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        if connection:
            try:
                connection.rollback()
            except:
                pass
            connection.close()
        raise
    except:
        # If exception occurs, don't return connection to pool
        if connection:
            try:
                connection.rollback()
            except:
                pass
            connection.close()
        raise


def close_db_connection():
    """Close all connections in pool"""
    global _pool
    for conn in _pool:
        try:
            conn.close()
        except:
            pass
    _pool = []


def test_connection():
    """Test database connection"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            logger.info("Database connection test successful")
            return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False
