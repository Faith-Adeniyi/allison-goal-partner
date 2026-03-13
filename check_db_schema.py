import sqlite3

DB_PATH = "app.db"


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='users';"
    )
    has_users_table = cur.fetchone() is not None

    if not has_users_table:
        conn.close()
        print("users table not found (DB likely not initialized yet).")
        return

    cur.execute("PRAGMA table_info(users)")
    cols = [row[1] for row in cur.fetchall()]
    conn.close()
    print(cols)


if __name__ == "__main__":
    main()
