#!/usr/bin/env python3
"""
Database helper: provides a MySQL connection wrapped to be SQLite-parameter compatible ('?' -> '%s').
Reads configuration from environment variables (via .env loaded by starter scripts).

Env variables:
  MYSQL_HOST (default: localhost)
  MYSQL_PORT (default: 3306)
  MYSQL_DATABASE (default: python_bot)
  MYSQL_USER (default: root)
  MYSQL_PASSWORD (default: root)
""" 

from __future__ import annotations

import os
import pymysql
from pymysql.cursors import Cursor
from typing import Any, Iterable, Optional, Sequence


MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "python_bot")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")


def _ensure_database_exists() -> None:
    """Ensure the target database exists. Requires a user with CREATE DATABASE privilege."""
    try:
        conn = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            autocommit=True,
        )
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    except Exception as e:
        # Non-fatal; API may still run if DB already exists
        print(f"[db] Warning: could not ensure database exists: {e}")
    finally:
        try:
            conn.close()  # type: ignore[name-defined]
        except Exception:
            pass


class CursorWrapper:
    """Wrap a PyMySQL cursor to accept SQLite-style '?' placeholders by converting them to '%s'."""

    def __init__(self, inner: Cursor):
        self._inner = inner

    def execute(self, query: str, params: Optional[Sequence[Any]] = None) -> int:
        if params is not None:
            query = query.replace("?", "%s")
        return self._inner.execute(query, params)

    def executemany(self, query: str, seq_of_params: Iterable[Sequence[Any]]) -> int:
        query = query.replace("?", "%s")
        return self._inner.executemany(query, seq_of_params)

    def fetchone(self) -> Optional[Sequence[Any]]:
        return self._inner.fetchone()

    def fetchall(self) -> list[Sequence[Any]]:
        return self._inner.fetchall()

    def close(self) -> None:
        self._inner.close()

    @property
    def rowcount(self) -> int:
        """Return the number of rows affected by the last execute() operation."""
        return self._inner.rowcount


class ConnectionWrapper:
    def __init__(self, inner):
        self._inner = inner

    def cursor(self) -> CursorWrapper:
        return CursorWrapper(self._inner.cursor())

    def commit(self) -> None:
        self._inner.commit()

    def rollback(self) -> None:
        self._inner.rollback()

    def close(self) -> None:
        self._inner.close()


def get_db_connection() -> ConnectionWrapper:
    """Return a MySQL connection wrapped to be SQLite-'?' compatible."""
    _ensure_database_exists()
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
        autocommit=False,
    )
    return ConnectionWrapper(conn)


def init_database() -> None:
    """Create required tables if missing (users, bots, bot_memories)."""
    conn = get_db_connection()
    cur = conn.cursor()

    # Users table
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS users (
            id VARCHAR(36) PRIMARY KEY,
            username VARCHAR(191) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP NULL DEFAULT NULL
        )
        '''
    )

    # Bots table
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS bots (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            name VARCHAR(191) NOT NULL,
            symbol VARCHAR(64) NOT NULL,
            network VARCHAR(64) NOT NULL,
            exchange_type VARCHAR(16) NOT NULL,
            exchange_type_value VARCHAR(64) NULL,
            min_time INT NOT NULL,
            max_time INT NOT NULL,
            min_spread DOUBLE NOT NULL,
            max_spread DOUBLE NOT NULL,
            buy_ratio DOUBLE NOT NULL,
            wallet_percentage INT NOT NULL,
            pause_volume BIGINT NOT NULL,
            api_key1 TEXT NULL,
            api_secret1 TEXT NULL,
            api_key2 TEXT NULL,
            api_secret2 TEXT NULL,
            status VARCHAR(16) DEFAULT 'inactive',
            process_id VARCHAR(64) NULL,
            started_at DATETIME NULL,
            uptime_seconds BIGINT NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_bots_user_id (user_id),
            CONSTRAINT fk_bots_user FOREIGN KEY (user_id) REFERENCES users (id)
                ON DELETE CASCADE ON UPDATE CASCADE
        )
        '''
    )

    # Backfill schema changes for existing installations using INFORMATION_SCHEMA checks
    try:
        # Helper to add a column only if it doesn't exist (compatible with MySQL/MariaDB versions)
        def _ensure_column(table: str, column: str, add_column_sql: str) -> None:
            try:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM information_schema.columns
                    WHERE table_schema = ? AND table_name = ? AND column_name = ?
                    """,
                    (MYSQL_DATABASE, table, column),
                )
                row = cur.fetchone()
                exists = (row[0] if row else 0) > 0
            except Exception as e:
                # If introspection fails, attempt to add and let DB decide
                print(f"[db] Warning: column existence check failed for {table}.{column}: {e}")
                exists = False

            if not exists:
                try:
                    cur.execute(add_column_sql)
                    print(f"[db] Added missing column {table}.{column}")
                except Exception as e:
                    # If another process added it in the meantime or any error occurs, log and continue
                    print(f"[db] Warning: could not add column {table}.{column}: {e}")

        _ensure_column(
            table="bots",
            column="started_at",
            add_column_sql="ALTER TABLE bots ADD COLUMN started_at DATETIME NULL",
        )
        _ensure_column(
            table="bots",
            column="uptime_seconds",
            add_column_sql="ALTER TABLE bots ADD COLUMN uptime_seconds BIGINT NOT NULL DEFAULT 0",
        )
    except Exception as e:
        print(f"[db] Warning: schema backfill failed: {e}")

    # Bot memories
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS bot_memories (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            name VARCHAR(191) NOT NULL,
            symbol VARCHAR(64) NOT NULL,
            network VARCHAR(64) NOT NULL,
            exchange_type VARCHAR(16) NOT NULL,
            exchange_type_value VARCHAR(64) NULL,
            min_time INT NOT NULL,
            max_time INT NOT NULL,
            min_spread DOUBLE NOT NULL,
            max_spread DOUBLE NOT NULL,
            buy_ratio DOUBLE NOT NULL,
            wallet_percentage INT NOT NULL,
            pause_volume BIGINT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_memories_user_id (user_id),
            CONSTRAINT fk_memories_user FOREIGN KEY (user_id) REFERENCES users (id)
                ON DELETE CASCADE ON UPDATE CASCADE
        )
        '''
    )

    conn.commit()
    conn.close()
