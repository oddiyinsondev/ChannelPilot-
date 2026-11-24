import logging
from datetime import datetime
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

import database
from config import TIMEZONE, DAILY_REPORT_HOUR, DAILY_REPORT_MINUTE
from handlers.post import publish_media_to_channel, get_post_url

logger = logging.getLogger(__name__)

def get_tz_now():
    tz = pytz.timezone(TIMEZONE)
    return datetime.now(tz)

async def check_scheduled_posts_job(bot: Bot):
    """Har daqiqada kutilayotgan postlarni tekshirib, vaqti kelganlarini chiqarish"""
    now_str = get_tz_now().strftime("%Y-%m-%d %H:%M:%S")
    pending_posts = await database.get_pending_scheduled_posts(now_str)

    for post in pending_posts:
        post_id = post["id"]
        channel_id = post["channel_id"]
        user_id = post["user_id"]
        media_type = post["media_type"]
        file_id = post.get("file_id")
        caption = post.get("caption")
        ch_title = post.get("channel_title", "Kanal")
        ch_username = post.get("channel_username")

        try:
            sent_msg = await publish_media_to_channel(bot, channel_id, media_type, file_id, caption)
            await database.mark_post_published(post_id, sent_msg.message_id)

            post_link = get_post_url(ch_username, channel_id, sent_msg.message_id)
            
            # Foydalanuvchiga bildirishnoma yuborish
            notify_text = (
                f"🔔 **Rejalashtirilgan post kanalga joylandi!**\n\n"
                f"📢 **Kanal:** {ch_title}\n"
                f"⏰ **Vaqti:** {now_str}\n"
                f"🔗 [Postni ko'rish]({post_link})"
            )
            try:
                await bot.send_message(user_id, notify_text, parse_mode="Markdown")
            except Exception:
                pass

        except TelegramAPIError as e:
            logger.error(f"Post {post_id} joylanmadi: {e.message}")
            await database.mark_post_failed(post_id)
            try:
                await bot.send_message(
                    user_id,
                    f"⚠️ **Post joylanmadi!**\n\n📢 Kanal: {ch_title}\n❌ Sabab: {e.message}"
                )
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Kutilmagan xatolik post {post_id}: {e}")
            await database.mark_post_failed(post_id)

async def format_channel_report(bot: Bot, channel: dict) -> str:
    """Bitta kanal bo'yicha hisobot matnini tayyorlash"""
    channel_id = channel["channel_id"]
    title = channel["title"]
    username = channel.get("username")
    uname_str = f"@{username}" if username else "Yopiq kanal"

    # Yangi a'zolar sonini olish
    try:
        current_members = await bot.get_chat_member_count(channel_id)
        await database.update_channel_members(channel_id, current_members)
    except Exception:
        current_members = channel.get("member_count", 0)

    start_members = channel.get("start_day_members") or current_members
    diff = current_members - start_members
    
    if diff > 0:
        diff_str = f"+{diff} ta 📈"
    elif diff < 0:
        diff_str = f"{diff} ta 📉"
    else:
        diff_str = "o'zgarishsiz (0)"

    # Bugungi postlarni olish
    today_posts = await database.get_today_posts_for_channel(channel_id)
    
    text = (
        f"📢 **Kanal:** {title} ({uname_str})\n"
        f"🆔 **ID:** `{channel_id}`\n"
        f"👥 **Hozirgi a'zolar soni:** {current_members:,} ta\n"
        f"📊 **Kunlik o'sish:** {diff_str}\n"
        f"📝 **Bugun joylangan postlar:** {len(today_posts)} ta\n"
    )

    if today_posts:
        text += "\n📋 **Joylashtirilgan postlar ro'yxati:**\n"
        for i, p in enumerate(today_posts, 1):
            p_time = p.get("published_at", "")[11:16] or "--:--"
            mtype = p.get("media_type", "matn").capitalize()
            cap = p.get("caption") or "(Matnsiz)"
            short_cap = cap[:35] + "..." if len(cap) > 35 else cap
            
            # Post havolasi
            msg_id = p.get("message_id")
            if msg_id:
                link = get_post_url(username, channel_id, msg_id)
                text += f"{i}. ⏰ `{p_time}` | {mtype} | \"{short_cap}\" — [Havola]({link})\n"
            else:
                text += f"{i}. ⏰ `{p_time}` | {mtype} | \"{short_cap}\"\n"
    else:
        text += "\nℹ️ *Bugun ushbu kanalga yangi post joylashtirilmadi.*\n"

    return text

async def daily_report_job(bot: Bot):
    """Har kuni soat 23:30 da barcha foydalanuvchilarga o'z kanallari hisobotini yuborish"""
    channels = await database.get_all_active_channels()
    if not channels:
        return

    # Foydalanuvchilar bo'yicha guruhlash
    users_channels = {}
    for ch in channels:
        uid = ch["user_id"]
        if uid not in users_channels:
            users_channels[uid] = []
        users_channels[uid].append(ch)

    now_date = get_tz_now().strftime("%d-%m-%Y")

    for user_id, u_channels in users_channels.items():
        try:
            report_header = (
                f"📊 **KUNLIK KANAL HISOBOTI (23:30)**\n"
                f"📅 **Sana:** {now_date}\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            )
            channel_reports = []
            for ch in u_channels:
                ch_text = await format_channel_report(bot, ch)
                channel_reports.append(ch_text)

            full_report = report_header + "\n━━━━━━━━━━━━━━━━━━━━━\n\n".join(channel_reports)
            full_report += "\n✨ *Ertangi kuningiz xayrli va sermahsul o'tsin!*"

            await bot.send_message(user_id, full_report, parse_mode="Markdown")
        except TelegramAPIError as e:
            logger.error(f"Foydalanuvchi {user_id} ga hisobot bormadi: {e.message}")
        except Exception as e:
            logger.error(f"Hisobot yuborishda xatolik user {user_id}: {e}")

async def midnight_reset_job():
    """Har yarim tunda (00:01) kun boshidagi obunachilar sonini yangilash"""
    await database.update_start_day_members_for_all()
    logger.info("Yangi kun uchun obunachilar boshlang'ich soni yangilandi.")

def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    tz = pytz.timezone(TIMEZONE)
    scheduler = AsyncIOScheduler(timezone=tz)

    # 1. Har daqiqada kutilayotgan postlarni tekshirish
    scheduler.add_job(
        check_scheduled_posts_job,
        trigger="interval",
        minutes=1,
        kwargs={"bot": bot},
        id="check_scheduled_posts",
        replace_existing=True
    )

    # 2. Har kuni soat 23:30 da kunlik hisobot yuborish
    scheduler.add_job(
        daily_report_job,
        trigger="cron",
        hour=DAILY_REPORT_HOUR,
        minute=DAILY_REPORT_MINUTE,
        kwargs={"bot": bot},
        id="daily_report_23_30",
        replace_existing=True
    )

    # 3. Har kecha 00:01 da yangi kun statistikasini yangilash
    scheduler.add_job(
        midnight_reset_job,
        trigger="cron",
        hour=0,
        minute=1,
        id="midnight_reset",
        replace_existing=True
    )

    return scheduler
