# database.py
import sqlite3
from config import DATABASE_PATH

def get_connection():
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -20000;")
    return conn

def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS recs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher TEXT NOT NULL,
            recommend INTEGER NOT NULL CHECK(recommend IN (0,1)),
            reason TEXT,
            user_id INTEGER NOT NULL,
            time DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(teacher, user_id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_teacher ON recs(teacher);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_teacher_recommend ON recs(teacher, recommend);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_time_desc ON recs(time DESC);")
    conn.commit()
    conn.close()

def add_evaluation(teacher: str, recommend: int, reason: str, user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO recs (teacher, recommend, reason, user_id) VALUES (?, ?, ?, ?)",
            (teacher, recommend, reason or "无理由", user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except:
        conn.rollback()
        return False
    finally:
        conn.close()

def get_teacher_detail(teacher: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT recommend, reason, substr(time, 1, 10) FROM recs WHERE teacher = ? ORDER BY time DESC",
        (teacher,)
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    yes_count = sum(1 for r in rows if r[0] == 1)
    no_count = len(rows) - yes_count
    reasons = [f"{'👍' if r[0] else '👎'} {r[1]} [{r[2]}]" for r in rows]

    return {"yes": yes_count, "no": no_count, "reasons": reasons}

def get_top_teachers(limit: int = 10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT teacher, SUM(recommend) as yes_count, COUNT(*) as total
        FROM recs GROUP BY teacher
        ORDER BY yes_count DESC LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_fuzzy_search(query: str, limit: int = 8):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT teacher, SUM(recommend) as yes_count, COUNT(*) as total
        FROM recs WHERE teacher LIKE ?
        GROUP BY teacher ORDER BY yes_count DESC LIMIT ?
    """, (f"%{query}%", limit))
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_teacher(teacher: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM recs WHERE teacher = ?", (teacher,))
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count

def user_has_rated(teacher: str, user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM recs WHERE teacher = ? AND user_id = ?", (teacher, user_id))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists
