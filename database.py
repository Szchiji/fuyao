# database.py
import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path
from config import DATABASE_PATH, MIN_REASON_LENGTH

def get_connection():
    """获取数据库连接"""
    # 确保目录存在
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn

def init_db():
    """初始化数据库表"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 创建评价表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher TEXT NOT NULL,
            recommend INTEGER NOT NULL,
            reason TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            time DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(teacher, user_id)
        )
    """)
    
    # 创建设置表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    # 创建索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_teacher ON recs(teacher)
    """)
    
    conn.commit()
    conn.close()

# 鼓励语和安慰语
ENCOURAGE_MESSAGES = [
    "✅ 感谢你的真实评价！你的反馈对其他狼友很有帮助～",
    "👍 评价成功！口碑库因为你又丰富了一点！",
    "❤️ 收到！你的评价已经记录，狼友们会感谢你。"
]

FAIL_MESSAGES = [
    "😔 理由有点简短呢～至少12个字哦",
    "💡 内容太简单了，试试写写具体感受",
    "⚠️ 可能包含敏感词，请修改后再试"
]

def get_encourage():
    """获取随机鼓励语"""
    return random.choice(ENCOURAGE_MESSAGES)

def get_fail_msg():
    """获取随机失败提示"""
    return random.choice(FAIL_MESSAGES)

def add_evaluation(teacher: str, recommend: int, reason: str, user_id: int) -> dict:
    """添加评价"""
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
    except Exception as e:
        return {"success": False, "msg": f"提交失败: {str(e)}"}
    finally:
        conn.close()

def get_teacher_detail(teacher: str):
    """获取教师评价详情"""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT recommend, reason, substr(time,1,10) FROM recs WHERE teacher = ? ORDER BY time DESC",
            (teacher,)
        ).fetchall()
        
        if not rows:
            return None
        
        yes = sum(1 for r in rows if r[0] == 1)
        no = len(rows) - yes
        reasons = [f"{'👍' if r[0] else '👎'} {r[1]} [{r[2]}]" for r in rows]
        
        return {
            "yes": yes,
            "no": no,
            "reasons": reasons,
            "total": len(rows)
        }
    finally:
        conn.close()

def get_global_stats():
    """获取全局统计"""
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM recs").fetchone()[0]
        teachers = conn.execute("SELECT COUNT(DISTINCT teacher) FROM recs").fetchone()[0]
        today = conn.execute("SELECT COUNT(*) FROM recs WHERE date(time) = date('now')").fetchone()[0]
        
        return {
            "total_eval": total,
            "total_teacher": teachers,
            "today": today
        }
    finally:
        conn.close()

def set_required_channel(channel_id: str):
    """设置必需频道"""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('channel', ?)",
            (channel_id,)
        )
        conn.commit()
    finally:
        conn.close()

def get_required_channel():
    """获取必需频道"""
    conn = get_connection()
    try:
        row = conn.execute("SELECT value FROM settings WHERE key = 'channel'").fetchone()
        return row[0] if row else None
    finally:
        conn.close()

def set_start_message(text: str):
    """设置开始消息"""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('start_msg', ?)",
            (text,)
        )
        conn.commit()
    finally:
        conn.close()

def get_start_message(default: str):
    """获取开始消息"""
    conn = get_connection()
    try:
        row = conn.execute("SELECT value FROM settings WHERE key = 'start_msg'").fetchone()
        return row[0] if row else default
    finally:
        conn.close()

def clean_old_data(days=90):
    """清理旧数据"""
    conn = get_connection()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        count = conn.execute("DELETE FROM recs WHERE time < ?", (cutoff,)).rowcount
        conn.commit()
        return count
    finally:
        conn.close()