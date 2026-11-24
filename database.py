import aiosqlite
from datetime import datetime
import pytz
from config import DATABASE_PATH, TIMEZONE

def get_now():
    tz = pytz.timezone(TIMEZONE)
    return datetime.now(tz)

def get_today_str():
    return get_now().strftime("%Y-%m-%d")

async def init_db():
    """Ma'lumotlar bazasi jadvallarini yaratish"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                username TEXT,
                invite_link TEXT,
                member_count INTEGER DEFAULT 0,
                start_day_members INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, channel_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER,
                media_type TEXT NOT NULL,
                file_id TEXT,
                caption TEXT,
                status TEXT DEFAULT 'pending',
                scheduled_at TIMESTAMP,
                published_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS channel_daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL,
                stat_date DATE NOT NULL,
                start_members INTEGER DEFAULT 0,
                end_members INTEGER DEFAULT 0,
                posts_count INTEGER DEFAULT 0,
                report_sent INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(channel_id, stat_date)
            )
        """)
        await db.commit()

# --- User metodlari ---
async def upsert_user(user_id: int, username: str | None, full_name: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name
        """, (user_id, username, full_name))
        await db.commit()

# --- Kanal metodlari ---
async def add_or_update_channel(user_id: int, channel_id: int, title: str, username: str | None, invite_link: str | None, member_count: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Avval kanal bor-yo'qligini tekshiramiz
        async with db.execute("SELECT start_day_members FROM channels WHERE user_id = ? AND channel_id = ?", (user_id, channel_id)) as cursor:
            row = await cursor.fetchone()
            start_members = row[0] if row and row[0] is not None else member_count

        await db.execute("""
            INSERT INTO channels (user_id, channel_id, title, username, invite_link, member_count, start_day_members, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(user_id, channel_id) DO UPDATE SET
                title = excluded.title,
                username = excluded.username,
                invite_link = excluded.invite_link,
                member_count = excluded.member_count,
                is_active = 1
        """, (user_id, channel_id, title, username, invite_link, member_count, start_members))
        await db.commit()

async def get_user_channels(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM channels 
            WHERE user_id = ? AND is_active = 1 
            ORDER BY added_at DESC
        """, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_user_channel(user_id: int, channel_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM channels 
            WHERE user_id = ? AND channel_id = ? AND is_active = 1
        """, (user_id, channel_id)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def delete_user_channel(user_id: int, channel_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            DELETE FROM channels 
            WHERE user_id = ? AND channel_id = ?
        """, (user_id, channel_id))
        await db.commit()

async def update_channel_members(channel_id: int, member_count: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE channels 
            SET member_count = ? 
            WHERE channel_id = ?
        """, (member_count, channel_id))
        await db.commit()

async def get_all_active_channels():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT DISTINCT c.*, u.full_name as user_name 
            FROM channels c
            JOIN users u ON c.user_id = u.user_id
            WHERE c.is_active = 1
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

# --- Post metodlari ---
async def save_post(user_id: int, channel_id: int, media_type: str, file_id: str | None, caption: str | None, status: str = 'pending', scheduled_at: str | None = None, message_id: int | None = None):
    now_str = get_now().strftime("%Y-%m-%d %H:%M:%S")
    published_at = now_str if status == 'published' else None
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO posts (user_id, channel_id, message_id, media_type, file_id, caption, status, scheduled_at, published_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, channel_id, message_id, media_type, file_id, caption, status, scheduled_at, published_at))
        await db.commit()
        return cursor.lastrowid

async def mark_post_published(post_id: int, message_id: int):
    now_str = get_now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE posts 
            SET status = 'published', message_id = ?, published_at = ?
            WHERE id = ?
        """, (message_id, now_str, post_id))
        await db.commit()

async def mark_post_failed(post_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE posts 
            SET status = 'failed'
            WHERE id = ?
        """, (post_id,))
        await db.commit()

async def get_pending_scheduled_posts(until_time_str: str):
    """Vaqti kelgan kutilayotgan postlarni olish"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT p.*, c.title as channel_title, c.username as channel_username
            FROM posts p
            JOIN channels c ON p.channel_id = c.channel_id AND p.user_id = c.user_id
            WHERE p.status = 'pending' AND p.scheduled_at <= ?
            ORDER BY p.scheduled_at ASC
        """, (until_time_str,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_user_pending_posts(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT p.*, c.title as channel_title
            FROM posts p
            JOIN channels c ON p.channel_id = c.channel_id
            WHERE p.user_id = ? AND p.status = 'pending'
            ORDER BY p.scheduled_at ASC
        """, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def delete_pending_post(post_id: int, user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            DELETE FROM posts
            WHERE id = ? AND user_id = ? AND status = 'pending'
        """, (post_id, user_id))
        await db.commit()

async def get_today_posts_for_channel(channel_id: int, date_str: str | None = None):
    if not date_str:
        date_str = get_today_str()
    start_time = f"{date_str} 00:00:00"
    end_time = f"{date_str} 23:59:59"
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM posts
            WHERE channel_id = ? AND status = 'published' AND published_at BETWEEN ? AND ?
            ORDER BY published_at ASC
        """, (channel_id, start_time, end_time)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def update_start_day_members_for_all():
    """Har yangi kun boshida barcha kanallarning a'zolari sonini start_day_members ga yozib qo'yish"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE channels
            SET start_day_members = member_count
        """)
        await db.commit()
