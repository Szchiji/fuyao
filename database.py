# database.py
import sqlite3
import random
from datetime import datetime, timedelta
from config import DATABASE_PATH, MIN_REASON_LENGTH

def get_connection():
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn

def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS recs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher TEXT NOT NULL,
            recommend INTEGER NOT NULL,
            reason TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            time DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(teacher, user_id)
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_teacher ON recs(teacher);
    """)
    conn.commit()
    conn.close()

# ====================== 鼓励语 & 失败安慰语 ======================
ENCOURAGE_MESSAGES = [
    "✅ 感谢你的真实评价！你的反馈对其他狼友很有帮助～",
    "👍 评价成功！口碑库因为你又丰富了一点！",
    "❤️ 收到！你的评价已经记录，狼友们会感谢你。",
    "🔥 干得漂亮！继续保持这种认真态度～"
]

FAIL_MESSAGES = [
    "😔 理由有点简短呢～至少12个字哦",
    "💡 内容太简单了，试试写写具体感受",
    "⚠️ 可能包含敏感词，请修改后再试",
    "📝 这个理由之前提交过类似内容，换个角度吧"
]

def get_encourage(): return random.choice(ENCOURAGE_MESSAGES)
def get_fail_msg(): return random.choice(FAIL_MESSAGES)

# ====================== 统计函数 ======================
def get_global_stats():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM recs").fetchone()[0]
    teachers = conn.execute("SELECT COUNT(DISTINCT teacher) FROM recs").fetchone()[0]
    today = conn.execute("SELECT COUNT(*) FROM recs WHERE date(time) = date('now')").fetchone()[0]
    conn.close()
    return {"total_eval": total, "total_teacher": teachers, "today": today}

# ====================== 设置函数 ======================
def set_required_channel(channel_id: str):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('channel', ?)", (channel_id,))
    conn.commit()
    conn.close()

def get_required_channel():
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = 'channel'").fetchone()
    conn.close()
    return row[0] if row else None

def set_start_message(text: str):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('start_msg', ?)", (text,))
    conn.commit()
    conn.close()

def get_start_message(default: str):
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = 'start_msg'").fetchone()
    conn.close()
    return row[0] if row else default

# ====================== 核心函数 ======================
def add_evaluation(teacher: str, recommend: int, reason: str, user_id: int) -> dict:
    if len(reason.strip()) < MIN_REASON_LENGTH:
        return {"success": False, "msg": "理由至少需要12个字"}
    
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO recs (teacher, recommend, reason, user_id) VALUES (?, ?, ?, ?)",
            (teacher.strip(), recommend, reason.strip(), user_id)
        )
        conn.commit()
        return {"success": True, "msg": "评价记录成功！"}
    except:
        conn.rollback()
        return {"success": False, "msg": "提交失败，可能已评价过"}
    finally:
        conn.close()

def get_teacher_detail(teacher: str):
    conn = get_connection()
    rows = conn.execute(
        "SELECT recommend, reason, substr(time,1,10) FROM recs WHERE teacher = ? ORDER BY time DESC",
        (teacher,)
    ).fetchall()
    conn.close()
    if not rows:
        return None
    yes = sum(1 for r in rows if r[0] == 1)
    no = len(rows) - yes
    reasons = [f"{'👍' if r[0] else '👎'} {r[1]} [{r[2]}]" for r in rows]
    return {"yes": yes, "no": no, "reasons": reasons, "total": len(rows)}

def clean_old_data(days=90):
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    count = conn.execute("DELETE FROM recs WHERE time < ?", (cutoff,)).rowcount
    conn.commit()
    conn.close()
    return count