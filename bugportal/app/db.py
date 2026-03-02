import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
BUG_MINING_DIR = BASE_DIR / "bug-mining"
BUG_CLASSIFICATION_DIR = BASE_DIR / "bug_classification"
DB_PATH = BASE_DIR / "bugportal" / "explainedrealbugs_meta.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_session():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create tables if not exist."""
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bug_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                bug_id TEXT NOT NULL,
                issue_id TEXT,
                issue_url TEXT,
                revision_buggy TEXT,
                revision_fixed TEXT,
                buggy_commit_url TEXT,
                fixed_commit_url TEXT,
                compare_url TEXT,
                source_type TEXT,
                title TEXT,
                description TEXT,
                discussion TEXT,
                llm_label TEXT,
                llm_full_text TEXT,
                UNIQUE(project_id, bug_id)
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bug_meta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                bug_id TEXT NOT NULL,
                manual_label TEXT,
                status TEXT,
                notes TEXT,
                tags TEXT,
                updated_at TEXT,
                UNIQUE(project_id, bug_id)
            );
            """
        )


if __name__ == "__main__":
    init_db()
    print(f"Initialized DB at {DB_PATH}")
