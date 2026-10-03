import sqlite3
from pathlib import Path


DB_PATH = Path("bot.db")


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS group_settings (
                chat_id INTEGER PRIMARY KEY,
                interval_minutes INTEGER NOT NULL DEFAULT 15,
                auto_price_enabled INTEGER NOT NULL DEFAULT 0
            )
        """)


def get_group_settings(chat_id):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT interval_minutes, auto_price_enabled
            FROM group_settings
            WHERE chat_id = ?
            """,
            (chat_id,)
        ).fetchone()

    if row is None:
        return {
            "interval_minutes": 15,
            "auto_price_enabled": False
        }

    return {
        "interval_minutes": row[0],
        "auto_price_enabled": bool(row[1])
    }


def save_group_settings(chat_id, interval_minutes, auto_price_enabled):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO group_settings
                (chat_id, interval_minutes, auto_price_enabled)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id)
            DO UPDATE SET
                interval_minutes = excluded.interval_minutes,
                auto_price_enabled = excluded.auto_price_enabled
            """,
            (
                chat_id,
                interval_minutes,
                int(auto_price_enabled)
            )
        )
