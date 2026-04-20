import shutil
import sqlite3
from pathlib import Path


DB_PATH = Path("habits.db")
BACKUP_PATH = Path("habits.pre_session_backup.db")


def get_existing_columns(cursor):
    rows = cursor.execute("PRAGMA table_info(habits)").fetchall()
    return {row[1] for row in rows}


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH.resolve()}")

    if not BACKUP_PATH.exists():
        shutil.copy2(DB_PATH, BACKUP_PATH)
        print(f"Backup created at: {BACKUP_PATH.resolve()}")
    else:
        print(f"Backup already exists at: {BACKUP_PATH.resolve()}")

    conn = sqlite3.connect(DB_PATH)

    try:
        cursor = conn.cursor()
        existing_columns = get_existing_columns(cursor)

        migrations = [
            ("is_session", "ALTER TABLE habits ADD COLUMN is_session BOOLEAN DEFAULT 0"),
            ("focus_time", "ALTER TABLE habits ADD COLUMN focus_time INTEGER"),
            ("break_time", "ALTER TABLE habits ADD COLUMN break_time INTEGER"),
            ("total_sessions", "ALTER TABLE habits ADD COLUMN total_sessions INTEGER"),
        ]

        applied = []

        for column_name, sql in migrations:
            if column_name not in existing_columns:
                cursor.execute(sql)
                applied.append(column_name)

        conn.commit()

        if applied:
            print("Added columns:", ", ".join(applied))
        else:
            print("No migration needed. Session columns already exist.")

        final_columns = get_existing_columns(cursor)
        print("Current habits columns:", ", ".join(sorted(final_columns)))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
