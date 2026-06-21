# -*- coding: utf-8 -*-
"""
Database connection manager — thread-safe for Flask.
Uses per-thread connections to avoid SQLite threading issues.
"""
import sqlite3
import threading
from config import DB_PATH


class DatabaseConnection:
    """Thread-safe SQLite connection manager."""

    def __init__(self, db_path: str = DB_PATH):
        self._db_path = db_path
        self._local = threading.local()

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create a connection for the current thread."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return self._local.conn

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor

    def executescript(self, script: str):
        conn = self._get_conn()
        conn.executescript(script)
        conn.commit()

    def fetch_one(self, query: str, params: tuple = ()) -> dict | None:
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def fetch_all(self, query: str, params: tuple = ()) -> list:
        cursor = self.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# Singleton instance
db = DatabaseConnection()
