import os
import threading
import psycopg2
import psycopg2.pool
from psycopg2.extras import execute_values, DictCursor
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

_DEFAULT_DSN = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:6432/stockbit_explorer"
)

# ---------------------------------------------------------------------------
# Thread-safe connection pool (singleton per DSN)
# ---------------------------------------------------------------------------

class ConnectionPool:
    """
    Thin wrapper around psycopg2.pool.ThreadedConnectionPool.

    A single shared pool is created lazily on first use and reused by all
    threads.  Use get_connection() as a context manager so connections are
    always returned to the pool even on error.
    """

    _instances: dict = {}
    _lock = threading.Lock()

    def __init__(self, dsn: str, minconn: int = 2, maxconn: int = 20):
        self.dsn = dsn
        self.minconn = minconn
        self.maxconn = maxconn
        self._pool = psycopg2.pool.ThreadedConnectionPool(minconn, maxconn, dsn)

    # ------------------------------------------------------------------
    # Factory: one pool per DSN
    # ------------------------------------------------------------------
    @classmethod
    def get_instance(cls, dsn: str = None, minconn: int = 2, maxconn: int = 20) -> "ConnectionPool":
        dsn = dsn or _DEFAULT_DSN
        with cls._lock:
            if dsn not in cls._instances:
                cls._instances[dsn] = cls(dsn, minconn, maxconn)
            else:
                existing = cls._instances[dsn]
                if maxconn > existing.maxconn:
                    try:
                        existing._pool.closeall()
                    except Exception:
                        pass
                    cls._instances[dsn] = cls(dsn, minconn, maxconn)
            return cls._instances[dsn]

    @classmethod
    def close_all(cls):
        """Close every pool (call at process shutdown)."""
        with cls._lock:
            for pool in cls._instances.values():
                try:
                    pool._pool.closeall()
                except Exception:
                    pass
            cls._instances.clear()

    # ------------------------------------------------------------------
    # Connection context manager
    # ------------------------------------------------------------------
    @contextmanager
    def get_connection(self):
        """
        Yields a psycopg2 connection from the pool.
        Auto-commits on success, rolls back on exception, always returns
        the connection to the pool.
        """
        conn = self._pool.getconn()
        conn.cursor_factory = DictCursor
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    # ------------------------------------------------------------------
    # High-performance batch helper
    # ------------------------------------------------------------------
    def execute_batch(self, query: str, data_tuples, page_size: int = 1000) -> int:
        """Insert *data_tuples* using psycopg2's fast execute_values."""
        if not data_tuples:
            return 0
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                execute_values(cur, query, data_tuples, page_size=page_size)
        return len(data_tuples)


# ---------------------------------------------------------------------------
# Legacy shim — keeps old DatabaseConnection API working
# ---------------------------------------------------------------------------

class DatabaseConnection:
    """
    Backward-compatible façade used by BaseRepository.
    Internally delegates to the shared ConnectionPool.
    """

    def __init__(self, dsn: str = None):
        self.dsn = dsn or _DEFAULT_DSN
        self._pool = ConnectionPool.get_instance(self.dsn)

    @contextmanager
    def get_connection(self):
        """Context-manager that yields a pooled connection."""
        with self._pool.get_connection() as conn:
            yield conn

    def execute_batch(self, query: str, data_tuples, page_size: int = 1000) -> int:
        return self._pool.execute_batch(query, data_tuples, page_size)


# Shared singleton (legacy import compat)
db_connection = DatabaseConnection()
