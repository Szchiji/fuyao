# database.py
"""
数据库操作模块
支持 SQLite 和 PostgreSQL
"""

import sqlite3
import logging
import os
from datetime import datetime
from config import MIN_REASON_LENGTH, DATABASE_URL, USE_POSTGRES

logger = logging.getLogger(__name__)

if USE_POSTGRES:
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        logger.info("✅ PostgreSQL 驱动已加载")
    except ImportError:
        logger.error("❌ 缺少 psycopg2，请运行: pip install psycopg2-binary")
        USE_POSTGRES = False
else:
    from config import DATABASE_PATH
    logger.info(f"📝 使用 SQLite: {DATABASE_PATH}")


def get_connection():
    """获取数据库连接"""
    if USE_POSTGRES:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            logger.debug("✅ PostgreSQL 连接成功")
            return conn
        except Exception as e:
            logger.error(f"❌ PostgreSQL 连接失败: {e}")
            raise
    else:
        try:
            from config import DATABASE_PATH
            db_dir = os.path.dirname(DATABASE_PATH)
            
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"📁 创建数据库目录: {db_dir}")
            
            conn = sqlite3.connect(DATABASE_PATH)
            conn.row_factory = sqlite3.Row
            logger.debug("✅ SQLite 连接成功")
            return conn
        except Exception as e:
            logger.error(f"❌ SQLite 连接失败: {e}")
            raise


def init_db():
    """初始化数据库"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRES:
            logger.info("📊 初始化 PostgreSQL 表...")
            
            # 评价表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recs (
                    id SERIAL PRIMARY KEY,
                    teacher TEXT NOT NULL,
                    user_id BIGINT NOT NULL,
                    recommend INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(teacher, user_id)
                )
            """)
            
            # 设置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            # 用户记录表（用于广播）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT DEFAULT '',
                    first_name TEXT DEFAULT '',
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 教师信息表（昵称和ID）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS teachers (
                    name TEXT PRIMARY KEY,
                    nickname TEXT DEFAULT '',
                    teacher_id TEXT DEFAULT ''
                )
            """)
            
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_teacher ON recs(teacher)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user ON recs(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_time ON recs(time)")
            except Exception:
                conn.rollback()
        else:
            logger.info("📊 初始化 SQLite 表...")
            
            # 评价表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    recommend INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(teacher, user_id)
                )
            """)
            
            # 设置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            # 用户记录表（用于广播）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT DEFAULT '',
                    first_name TEXT DEFAULT '',
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 教师信息表（昵称和ID）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS teachers (
                    name TEXT PRIMARY KEY,
                    nickname TEXT DEFAULT '',
                    teacher_id TEXT DEFAULT ''
                )
            """)
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_teacher ON recs(teacher)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user ON recs(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_time ON recs(time)")
        
        conn.commit()
        conn.close()
        
        db_info = "PostgreSQL" if USE_POSTGRES else "SQLite"
        logger.info(f"✅ {db_info} 数据库初始化成功")
    
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        raise


def check_user_rated_teacher(teacher: str, user_id: int) -> bool:
    """检查用户是否已评价该教师"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRES:
            cursor.execute("SELECT id FROM recs WHERE teacher = %s AND user_id = %s", (teacher, user_id))
        else:
            cursor.execute("SELECT id FROM recs WHERE teacher = ? AND user_id = ?", (teacher, user_id))
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    except Exception as e:
        logger.error(f"检查评价记录时出错: {e}")
        return False


def add_evaluation(teacher: str, recommend: int, reason: str, user_id: int) -> dict:
    """添加评价"""
    if len(reason.strip()) < MIN_REASON_LENGTH:
        return {
            "success": False,
            "msg": f"❌ 理由太短！至少需要 {MIN_REASON_LENGTH} 个字\n\n您填写的: {len(reason)} 个字"
        }
    
    if check_user_rated_teacher(teacher, user_id):
        return {
            "success": False,
            "msg": f"❌ 您已经评价过 @{teacher} 了\n\n每个教师只能评价一次"
        }
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRES:
            cursor.execute(
                "INSERT INTO recs (teacher, user_id, recommend, reason) VALUES (%s, %s, %s, %s)",
                (teacher, user_id, recommend, reason)
            )
        else:
            cursor.execute(
                "INSERT INTO recs (teacher, user_id, recommend, reason) VALUES (?, ?, ?, ?)",
                (teacher, user_id, recommend, reason)
            )
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ 用户 {user_id} 成功评价了 {teacher}")
        return {
            "success": True,
            "msg": "✅ 评价提交成功！\n\n感谢您的反馈！"
        }
    
    except Exception as e:
        logger.error(f"添加评价失败: {e}")
        return {
            "success": False,
            "msg": f"❌ 提交失败: {str(e)}"
        }


def get_teacher_stats(teacher: str) -> dict:
    """获取教师的评价统计"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRES:
            cursor.execute("SELECT COUNT(*) FROM recs WHERE teacher = %s", (teacher,))
            total = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM recs WHERE teacher = %s AND recommend = 1", (teacher,))
            recommend_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM recs WHERE teacher = %s AND recommend = 0", (teacher,))
            not_recommend_count = cursor.fetchone()[0]
            
            cursor.execute(
                "SELECT id, user_id, recommend, reason, time FROM recs WHERE teacher = %s ORDER BY time DESC LIMIT 3",
                (teacher,)
            )
            latest = cursor.fetchall()
        else:
            cursor.execute("SELECT COUNT(*) FROM recs WHERE teacher = ?", (teacher,))
            total = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM recs WHERE teacher = ? AND recommend = 1", (teacher,))
            recommend_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM recs WHERE teacher = ? AND recommend = 0", (teacher,))
            not_recommend_count = cursor.fetchone()[0]
            
            cursor.execute(
                "SELECT id, user_id, recommend, reason, time FROM recs WHERE teacher = ? ORDER BY time DESC LIMIT 3",
                (teacher,)
            )
            latest = cursor.fetchall()
        
        conn.close()
        
        return {
            "teacher": teacher,
            "total": total,
            "recommend": recommend_count,
            "not_recommend": not_recommend_count,
            "latest": latest
        }
    except Exception as e:
        logger.error(f"获取教师统计失败: {e}")
        return {
            "teacher": teacher,
            "total": 0,
            "recommend": 0,
            "not_recommend": 0,
            "latest": []
        }


def get_global_stats() -> dict:
    """获取全局统计"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRES:
            cursor.execute("SELECT COUNT(*) FROM recs")
            total_eval = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT teacher) FROM recs")
            total_teacher = cursor.fetchone()[0]
            
            today = datetime.now().date()
            cursor.execute("SELECT COUNT(*) FROM recs WHERE DATE(time) = %s", (today,))
            today_count = cursor.fetchone()[0]
        else:
            cursor.execute("SELECT COUNT(*) FROM recs")
            total_eval = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT teacher) FROM recs")
            total_teacher = cursor.fetchone()[0]
            
            today = datetime.now().date()
            cursor.execute("SELECT COUNT(*) FROM recs WHERE DATE(time) = ?", (today,))
            today_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_eval": total_eval,
            "total_teacher": total_teacher,
            "today": today_count
        }
    except Exception as e:
        logger.error(f"获取全局统计失败: {e}")
        return {
            "total_eval": 0,
            "total_teacher": 0,
            "today": 0
        }


def add_required_channel(channel_id: str) -> dict:
    """添加频道要求"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRES:
            cursor.execute(
                "SELECT value FROM settings WHERE key = %s", 
                (f"channel_{channel_id}",)
            )
            if cursor.fetchone():
                conn.close()
                logger.warning(f"⚠️ 频道 {channel_id} 已添加过了")
                return {
                    "success": False,
                    "msg": f"❌ 频道 {channel_id} 已添加过了"
                }
            
            cursor.execute(
                "INSERT INTO settings (key, value) VALUES (%s, %s)",
                (f"channel_{channel_id}", channel_id)
            )
        else:
            cursor.execute(
                "SELECT value FROM settings WHERE key = ?", 
                (f"channel_{channel_id}",)
            )
            if cursor.fetchone():
                conn.close()
                logger.warning(f"⚠️ 频道 {channel_id} 已添加过了")
                return {
                    "success": False,
                    "msg": f"❌ 频道 {channel_id} 已添加过了"
                }
            
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (f"channel_{channel_id}", channel_id)
            )
        
        conn.commit()
        conn.close()
        logger.info(f"✅ 频道已添加: {channel_id}")
        return {
            "success": True,
            "msg": f"✅ 频道 {channel_id} 已添加"
        }
    except Exception as e:
        logger.error(f"添加频道失败: {e}")
        return {
            "success": False,
            "msg": f"❌ 添加频道失败: {str(e)}"
        }


def get_all_required_channels() -> list:
    """获取所有频道要求"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRES:
            cursor.execute("SELECT value FROM settings WHERE key LIKE %s", ('channel_%',))
        else:
            cursor.execute("SELECT value FROM settings WHERE key LIKE ?", ('channel_%',))
        
        results = cursor.fetchall()
        conn.close()
        
        channels = [r[0] for r in results] if results else []
        logger.info(f"📋 获取到 {len(channels)} 个频道: {channels}")
        return channels
    except Exception as e:
        logger.error(f"获取频道列表失败: {e}")
        return []


def remove_required_channel(channel_id: str) -> dict:
    """移除频道要求"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRES:
            cursor.execute(
                "DELETE FROM settings WHERE key = %s", 
                (f"channel_{channel_id}",)
            )
        else:
            cursor.execute(
                "DELETE FROM settings WHERE key = ?", 
                (f"channel_{channel_id}",)
            )
        
        conn.commit()
        conn.close()
        logger.info(f"✅ 频道已移除: {channel_id}")
        return {
            "success": True,
            "msg": f"✅ 频道 {channel_id} 已移除"
        }
    except Exception as e:
        logger.error(f"移除频道失败: {e}")
        return {
            "success": False,
            "msg": f"❌ 移除频道失败: {str(e)}"
        }


def set_start_message(message: str):
    """设置欢迎语"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRES:
            cursor.execute(
                "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = %s",
                ("start_message", message, message)
            )
        else:
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                ("start_message", message)
            )
        
        conn.commit()
        conn.close()
        logger.info("✅ 欢迎语已设置")
    except Exception as e:
        logger.error(f"设置欢迎语失败: {e}")


def get_start_message(default: str = "") -> str:
    """获取欢迎语"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRES:
            cursor.execute("SELECT value FROM settings WHERE key = %s", ("start_message",))
        else:
            cursor.execute("SELECT value FROM settings WHERE key = ?", ("start_message",))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else default
    except Exception as e:
        logger.error(f"获取欢迎语失败: {e}")
        return default


def set_start_buttons(buttons: list):
    """保存欢迎语按钮（列表形式 [{"text": ..., "url": ...}, ...]）"""
    import json
    try:
        value = json.dumps(buttons, ensure_ascii=False)
        conn = get_connection()
        cursor = conn.cursor()
        if USE_POSTGRES:
            cursor.execute(
                "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = %s",
                ("start_message_buttons", value, value)
            )
        else:
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                ("start_message_buttons", value)
            )
        conn.commit()
        conn.close()
        logger.info(f"✅ 欢迎语按钮已保存，共 {len(buttons)} 个")
    except Exception as e:
        logger.error(f"保存欢迎语按钮失败: {e}")


def get_start_buttons() -> list:
    """获取欢迎语按钮列表"""
    import json
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if USE_POSTGRES:
            cursor.execute("SELECT value FROM settings WHERE key = %s", ("start_message_buttons",))
        else:
            cursor.execute("SELECT value FROM settings WHERE key = ?", ("start_message_buttons",))
        result = cursor.fetchone()
        conn.close()
        if result and result[0]:
            return json.loads(result[0])
        return []
    except Exception as e:
        logger.error(f"获取欢迎语按钮失败: {e}")
        return []


def record_user(user_id: int, username: str = "", first_name: str = ""):
    """记录使用过机器人的用户（用于广播）"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        uname = username or ""
        fname = first_name or ""
        if USE_POSTGRES:
            cursor.execute(
                """INSERT INTO users (user_id, username, first_name)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (user_id) DO UPDATE SET username = %s, first_name = %s""",
                (user_id, uname, fname, uname, fname)
            )
        else:
            cursor.execute(
                "INSERT OR REPLACE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                (user_id, uname, fname)
            )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"记录用户失败: {e}")


def get_all_user_ids() -> list:
    """获取所有曾使用过机器人的用户 ID"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        rows = cursor.fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        return []


def set_teacher_info(name: str, nickname: str = "", teacher_id: str = ""):
    """设置教师昵称和ID"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if USE_POSTGRES:
            cursor.execute(
                """INSERT INTO teachers (name, nickname, teacher_id)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (name) DO UPDATE SET nickname = %s, teacher_id = %s""",
                (name, nickname, teacher_id, nickname, teacher_id)
            )
        else:
            cursor.execute(
                "INSERT OR REPLACE INTO teachers (name, nickname, teacher_id) VALUES (?, ?, ?)",
                (name, nickname, teacher_id)
            )
        conn.commit()
        conn.close()
        logger.info(f"✅ 教师 @{name} 信息已更新")
    except Exception as e:
        logger.error(f"设置教师信息失败: {e}")


def get_teacher_info(name: str) -> dict:
    """获取教师昵称和ID，未设置则返回空字符串"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if USE_POSTGRES:
            cursor.execute("SELECT nickname, teacher_id FROM teachers WHERE name = %s", (name,))
        else:
            cursor.execute("SELECT nickname, teacher_id FROM teachers WHERE name = ?", (name,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"nickname": row[0] or "", "teacher_id": row[1] or ""}
        return {"nickname": "", "teacher_id": ""}
    except Exception as e:
        logger.error(f"获取教师信息失败: {e}")
        return {"nickname": "", "teacher_id": ""}


def get_teacher_reviews_page(teacher: str, page: int = 0, per_page: int = 5) -> list:
    """分页获取教师评价（用于"更多评价"按钮）"""
    try:
        offset = page * per_page
        conn = get_connection()
        cursor = conn.cursor()
        if USE_POSTGRES:
            cursor.execute(
                "SELECT id, user_id, recommend, reason, time FROM recs"
                " WHERE teacher = %s ORDER BY time DESC LIMIT %s OFFSET %s",
                (teacher, per_page, offset)
            )
        else:
            cursor.execute(
                "SELECT id, user_id, recommend, reason, time FROM recs"
                " WHERE teacher = ? ORDER BY time DESC LIMIT ? OFFSET ?",
                (teacher, per_page, offset)
            )
        rows = cursor.fetchall()
        conn.close()
        return rows if rows else []
    except Exception as e:
        logger.error(f"分页获取教师评价失败: {e}")
        return []


def get_encourage() -> str:
    """获取随机鼓励语"""
    encourages = [
        "✅ 评价提交成功！感谢您的反馈！",
        "🎉 评价已保存！您的意见很重要！",
        "👍 提交成功！帮助了其他同学！",
        "⭐ 评价完成！谢谢您的参与！",
        "🌟 成功保存！您的建议已记录！"
    ]
    
    import random
    return random.choice(encourages)


# ==================== 教师数据删除函数 ====================

def delete_teacher_data_from_db(teacher: str) -> dict:
    """
    删除某个教师的所有评价数据
    
    Args:
        teacher: 教师名称
    
    Returns:
        删除结果
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 先获��统计信息
        if USE_POSTGRES:
            cursor.execute("SELECT COUNT(*) FROM recs WHERE teacher = %s", (teacher,))
            total = cursor.fetchone()[0]
            
            # 删除数据
            cursor.execute("DELETE FROM recs WHERE teacher = %s", (teacher,))
        else:
            cursor.execute("SELECT COUNT(*) FROM recs WHERE teacher = ?", (teacher,))
            total = cursor.fetchone()[0]
            
            # 删除数据
            cursor.execute("DELETE FROM recs WHERE teacher = ?", (teacher,))
        
        conn.commit()
        conn.close()
        
        logger.warning(f"🗑️ 已删除教师 @{teacher} 的 {total} 条评价数据")
        
        return {
            "success": True,
            "msg": f"""✅ 教师数据已删除

教师: @{teacher}
删除数: {total} 条评价

数据已从数据库中永久删除"""
        }
    
    except Exception as e:
        logger.error(f"删除教师数据失败: {e}")
        return {
            "success": False,
            "msg": f"❌ 删除失败: {str(e)}"
        }


def delete_user_rating(teacher: str, user_id: int) -> dict:
    """
    删除某个用户对某个教师的评价
    
    Args:
        teacher: 教师名称
        user_id: 用户 ID
    
    Returns:
        删除结果
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRES:
            cursor.execute(
                "DELETE FROM recs WHERE teacher = %s AND user_id = %s",
                (teacher, user_id)
            )
        else:
            cursor.execute(
                "DELETE FROM recs WHERE teacher = ? AND user_id = ?",
                (teacher, user_id)
            )
        
        conn.commit()
        conn.close()
        
        logger.warning(f"🗑️ 已删除用户 {user_id} 对教师 @{teacher} 的评价")
        
        return {
            "success": True,
            "msg": f"✅ 评价已删除"
        }
    
    except Exception as e:
        logger.error(f"删除评价失败: {e}")
        return {
            "success": False,
            "msg": f"❌ 删除失败: {str(e)}"
        }


def get_teacher_detail(teacher: str):
    """
    获取教师的评价详情（推荐数、不推荐数及理由列表）

    Args:
        teacher: 教师名称

    Returns:
        dict with keys 'yes', 'no', 'reasons', or None if no records exist
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        if USE_POSTGRES:
            cursor.execute("SELECT COUNT(*) FROM recs WHERE teacher = %s", (teacher,))
            total = cursor.fetchone()[0]

            if total == 0:
                conn.close()
                return None

            cursor.execute(
                "SELECT COUNT(*) FROM recs WHERE teacher = %s AND recommend = 1", (teacher,)
            )
            yes_count = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM recs WHERE teacher = %s AND recommend = 0", (teacher,)
            )
            no_count = cursor.fetchone()[0]

            cursor.execute(
                "SELECT reason FROM recs WHERE teacher = %s ORDER BY time DESC", (teacher,)
            )
            reasons = [row[0] for row in cursor.fetchall()]
        else:
            cursor.execute("SELECT COUNT(*) FROM recs WHERE teacher = ?", (teacher,))
            total = cursor.fetchone()[0]

            if total == 0:
                conn.close()
                return None

            cursor.execute(
                "SELECT COUNT(*) FROM recs WHERE teacher = ? AND recommend = 1", (teacher,)
            )
            yes_count = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM recs WHERE teacher = ? AND recommend = 0", (teacher,)
            )
            no_count = cursor.fetchone()[0]

            cursor.execute(
                "SELECT reason FROM recs WHERE teacher = ? ORDER BY time DESC", (teacher,)
            )
            reasons = [row[0] for row in cursor.fetchall()]

        conn.close()

        return {
            "yes": yes_count,
            "no": no_count,
            "reasons": reasons,
        }

    except Exception as e:
        logger.error(f"获取教师详情失败: {e}")
        return None


def get_teacher_all_ratings(teacher: str) -> list:
    """
    获取某个教师的所有评价
    
    Args:
        teacher: 教师名称
    
    Returns:
        评价列表
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRES:
            cursor.execute(
                "SELECT id, user_id, recommend, reason, time FROM recs WHERE teacher = %s ORDER BY time DESC",
                (teacher,)
            )
        else:
            cursor.execute(
                "SELECT id, user_id, recommend, reason, time FROM recs WHERE teacher = ? ORDER BY time DESC",
                (teacher,)
            )
        
        results = cursor.fetchall()
        conn.close()
        
        return results if results else []
    
    except Exception as e:
        logger.error(f"获取教师评价失败: {e}")
        return []


def get_leaderboard(limit: int = 10) -> list:
    """
    获取教师排行榜（按推荐数降序，推荐数相同则按总评价数降序）

    Args:
        limit: 返回的教师数量，默认 10

    Returns:
        列表，每项为 dict: teacher, total, recommend, not_recommend, recommend_pct
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        if USE_POSTGRES:
            cursor.execute(
                """
                SELECT teacher,
                       COUNT(*) AS total,
                       SUM(CASE WHEN recommend = 1 THEN 1 ELSE 0 END) AS recommend_count,
                       SUM(CASE WHEN recommend = 0 THEN 1 ELSE 0 END) AS not_recommend_count
                FROM recs
                GROUP BY teacher
                ORDER BY recommend_count DESC, total DESC
                LIMIT %s
                """,
                (limit,)
            )
        else:
            cursor.execute(
                """
                SELECT teacher,
                       COUNT(*) AS total,
                       SUM(CASE WHEN recommend = 1 THEN 1 ELSE 0 END) AS recommend_count,
                       SUM(CASE WHEN recommend = 0 THEN 1 ELSE 0 END) AS not_recommend_count
                FROM recs
                GROUP BY teacher
                ORDER BY recommend_count DESC, total DESC
                LIMIT ?
                """,
                (limit,)
            )

        rows = cursor.fetchall()
        conn.close()

        result = []
        for row in rows:
            total = row[1]
            recommend = row[2]
            not_recommend = row[3]
            pct = int(recommend / total * 100) if total > 0 else 0
            result.append({
                "teacher": row[0],
                "total": total,
                "recommend": recommend,
                "not_recommend": not_recommend,
                "recommend_pct": pct,
            })
        return result

    except Exception as e:
        logger.error(f"获取排行榜失败: {e}")
        return []


def delete_rating_by_id(rating_id: str, teacher: str) -> dict:
    """删除指定 ID 的评价"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRES:
            cursor.execute("DELETE FROM recs WHERE id = %s AND teacher = %s", (int(rating_id), teacher))
        else:
            cursor.execute("DELETE FROM recs WHERE id = ? AND teacher = ?", (int(rating_id), teacher))
        
        conn.commit()
        conn.close()
        
        logger.warning(f"🗑️ 删除了评价 ID: {rating_id}")
        
        return {
            "success": True,
            "msg": f"✅ 评价已删除"
        }
    except Exception as e:
        logger.error(f"删除评价失败: {e}")
        return {
            "success": False,
            "msg": f"❌ 删除失败: {str(e)}"
        }