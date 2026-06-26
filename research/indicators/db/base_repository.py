import os
import psycopg2
from psycopg2.extras import DictCursor
from .connection import DatabaseConnection, ConnectionPool, _DEFAULT_DSN

class BaseRepository:
    """
    Base class for all domain repositories.

    Uses a shared ThreadedConnectionPool so every worker thread gets its own
    psycopg2 connection from the pool without creating/closing connections
    on every call.

    Usage (in subclasses):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(...)
    """

    def __init__(self, db_dsn=None):
        dsn = db_dsn or _DEFAULT_DSN

        if db_dsn and not (
            db_dsn.startswith("postgres://") or db_dsn.startswith("postgresql://")
        ):
            raise ValueError(
                f"Invalid database connection: '{db_dsn}'. "
                "SQLite file-based database paths are no longer supported. "
                "Please provide a valid PostgreSQL DSN starting with 'postgres://' or 'postgresql://'."
            )

        # All repositories share the same pool for the same DSN
        self._pool = ConnectionPool.get_instance(dsn)
        # Keep legacy connection_manager attribute for any code that uses it
        self.connection_manager = DatabaseConnection(dsn)

    def get_connection(self):
        """
        Returns a context manager that yields a pooled psycopg2 connection.

        The connection is auto-committed on success and rolled back on
        exception, then returned to the pool.
        """
        return self._pool.get_connection()

    @classmethod
    def init_pool(cls, dsn: str, minconn: int = 2, maxconn: int = 20):
        """
        Pre-initialise the shared connection pool.
        Call this once at startup (e.g. in backloader main()) before spawning
        worker threads so the pool is sized correctly from the start.
        """
        ConnectionPool.get_instance(dsn, minconn=minconn, maxconn=maxconn)

    @classmethod
    def close_pool(cls):
        """Shutdown all connection pools (call at process exit)."""
        ConnectionPool.close_all()
