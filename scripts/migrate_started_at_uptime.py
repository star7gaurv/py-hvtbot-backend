#!/usr/bin/env python3
"""
One-time migration to add uptime tracking columns to the 'bots' table:
  - started_at DATETIME NULL
  - uptime_seconds BIGINT NOT NULL DEFAULT 0

Safe to run multiple times; it checks INFORMATION_SCHEMA before altering.
Reads MySQL connection settings from environment (.env loaded by start scripts).
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
import os

# Ensure we can import top-level db module
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

# Load env before importing db, so db picks up correct values
env_path = parent_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"[info] Loaded environment from {env_path}")
else:
    print("[info] No .env found, using process environment/defaults")

from db import get_db_connection, MYSQL_DATABASE  # type: ignore


def ensure_column(cur, table: str, column: str, add_sql: str) -> None:
    cur.execute(
        """
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_schema = ? AND table_name = ? AND column_name = ?
        """,
        (MYSQL_DATABASE, table, column),
    )
    row = cur.fetchone()
    exists = (row[0] if row else 0) > 0
    if exists:
        print(f"[ok] Column {table}.{column} already exists")
        return
    try:
        cur.execute(add_sql)
        print(f"[ok] Added column {table}.{column}")
    except Exception as e:
        print(f"[warn] Could not add {table}.{column}: {e}")


def main():
    conn = get_db_connection()
    cur = conn.cursor()

    ensure_column(cur, "bots", "started_at", "ALTER TABLE bots ADD COLUMN started_at DATETIME NULL")
    ensure_column(cur, "bots", "uptime_seconds", "ALTER TABLE bots ADD COLUMN uptime_seconds BIGINT NOT NULL DEFAULT 0")

    conn.commit()
    conn.close()
    print("[done] Migration complete.")


if __name__ == "__main__":
    main()
