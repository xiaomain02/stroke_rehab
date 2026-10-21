"""SQLite persistence for accounts and API resources."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DATABASE_PATH = Path(os.environ.get("AUTH_DATABASE_PATH", "auth.sqlite3"))


class _ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect() -> sqlite3.Connection:
    db = sqlite3.connect(DATABASE_PATH, timeout=10, factory=_ClosingConnection)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('patient', 'doctor')),
            doctor_id INTEGER REFERENCES users(id),
            password_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('motor', 'speech', 'memory')),
            description TEXT NOT NULL,
            video_url TEXT
        );
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL REFERENCES users(id),
            doctor_id INTEGER NOT NULL REFERENCES users(id),
            exercise_id INTEGER NOT NULL REFERENCES exercises(id),
            due_date TEXT,
            times_per_week INTEGER NOT NULL CHECK(times_per_week > 0),
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL REFERENCES assignments(id),
            patient_id INTEGER NOT NULL REFERENCES users(id),
            exercise_id INTEGER NOT NULL REFERENCES exercises(id),
            score REAL NOT NULL CHECK(score >= 0 AND score <= 100),
            duration_sec INTEGER NOT NULL CHECK(duration_sec >= 0),
            errors INTEGER NOT NULL CHECK(errors >= 0),
            details TEXT,
            media_url TEXT,
            media_type TEXT,
            media_content_type TEXT,
            media BLOB,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS diaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL REFERENCES users(id),
            date TEXT NOT NULL,
            mood INTEGER NOT NULL CHECK(mood BETWEEN 1 AND 5),
            fatigue INTEGER NOT NULL CHECK(fatigue BETWEEN 1 AND 5),
            note TEXT
        );
        CREATE TABLE IF NOT EXISTS exercise_media (
            exercise_id INTEGER PRIMARY KEY REFERENCES exercises(id),
            content_type TEXT NOT NULL,
            filename TEXT NOT NULL,
            content BLOB NOT NULL
        );
        """
    )
    result_columns = {row["name"] for row in db.execute("PRAGMA table_info(results)")}
    if "media_content_type" not in result_columns:
        db.execute("ALTER TABLE results ADD COLUMN media_content_type TEXT")
    if db.execute("SELECT COUNT(*) FROM exercises").fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO exercises(title, type, description) VALUES (?, ?, ?)",
            [
                ("Reach the target", "motor", "Practice reaching toward a visual target."),
                ("Repeat the word", "speech", "Listen to a word and practice saying it."),
                ("Remember the sequence", "memory", "Recall a short sequence in the correct order."),
            ],
        )
    return db
