import re
from datetime import datetime, timedelta
import pytz
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramAPIError

import database
from config import TIMEZONE, PEAK_HOURS
from states import PostState
from keyboards import (
    get_main_keyboard,
    get_post_target_channels_inline,
    get_post_schedule_inline,
    get_pending_post_item_inline,
    get_cancel_inline
)

router = Router()

def get_tz_now():
    tz = pytz.timezone(TIMEZONE)
    return datetime.now(tz)

def calculate_next_peak_time():
    """Keyingi eng yaqin faol soatni hisoblash (09:00, 13:00, 18:30, 21:00)"""
    now = get_tz_now()
    today = now.date()
    tz = pytz.timezone(TIMEZONE)

    for peak in PEAK_HOURS:
        peak_dt = tz.localize(datetime(today.year, today.month, today.day, peak["hour"], peak["minute"], 0))
        # Agar bu vaqtga kamida 5 daqiqa qolgan bo'lsa
        if peak_dt > now + timedelta(minutes=5):
            return peak_dt, peak["label"]

    # Agar bugungi barcha faol soatlar o'tgan bo'lsa, ertangi birinchi faol vaqt
    tomorrow = today + timedelta(days=1)
    first_peak = PEAK_HOURS[0]
    next_dt = tz.localize(datetime(tomorrow.year, tomorrow.month, tomorrow.day, first_peak["hour"], first_peak["minute"], 0))
    return next_dt, f"Ertaga {first_peak['label']}"

async def publish_media_to_channel(bot: Bot, channel_id: int, media_type: str, file_id: str | None, caption: str | None):
    """Kanalga media yoki matnni yuborish"""
    if media_type == "photo":
        return await bot.send_photo(chat_id=channel_id, photo=file_id, caption=caption)
    elif media_type == "video":
        return await bot.send_video(chat_id=channel_id, video=file_id, caption=caption)
    elif media_type == "animation":
        return await bot.send_animation(chat_id=channel_id, animation=file_id, caption=caption)
    elif media_type == "document":
        return await bot.send_document(chat_id=channel_id, document=file_id, caption=caption)
    elif media_type == "audio":
        return await bot.send_audio(chat_id=channel_id, audio=file_id, caption=caption)
    else:
        return await bot.send_message(chat_id=channel_id, text=caption or "")

def get_post_url(channel_username: str | None, channel_id: int, message_id: int) -> str:
    """Post uchun havola generatsiya qilish"""
    if channel_username:
        return f"https://t.me/{channel_username}/{message_id}"
    clean_id = str(channel_id).replace("-100", "")
    return f"https://t.me/c/{clean_id}/{message_id}"

# 1. Post yozish tugmasi bosilganda
@router.message(F.text == "✍️ Post yuborish")
async def start_create_post(message: Message, state: FSMContext):
    user_id = message.from_user.id
    channels = await database.get_user_channels(user_id)
    
    if not channels:
        await message.answer(
            "⚠️ **Sizda hali birorta kanal ulanmagan!**\n\n"
            "Post yuborish uchun avval **➕ Kanal qo'shish** tugmasini bosing va o'z kanalingizni ulang.",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
        return

    await state.set_state(PostState.waiting_for_content)
    await message.answer(
        "✍️ **Post mazmunini yuboring:**\n\n"
        "Siz quyidagilardan birini yuborishingiz mumkin:\n"
        "• 📸 Rasm (tagiga matn / caption bilan)\n"
        "• 🎬 Video (tagiga matn / caption bilan)\n"
        "• 🎞 GIF (Animation)\n"
        "• 📝 Oddiy matnli xabar\n\n"
        "Bekor qilish uchun: /cancel",
        reply_markup=get_cancel_inline(),
        parse_mode="Markdown"
    )

# Kanal tafsilotidan to'g'ridan-to'g'ri shu kanalga post yozish
@router.callback_query(F.data.startswith("ch_post_"))
async def start_create_post_for_channel(callback: CallbackQuery, state: FSMContext):
    channel_id = int(callback.data.replace("ch_post_", ""))
    user_id = callback.from_user.id
    
    channel = await database.get_user_channel(user_id, channel_id)
    if not channel:
        await callback.answer("⚠️ Kanal topilmadi!", show_alert=True)
        return

    await state.set_state(PostState.waiting_for_content)
    await state.update_data(preselected_channel_id=channel_id)
    
    await callback.message.answer(
        f"✍️ **'{channel['title']}' kanali uchun post yuboring:**\n\n"
        f"Rasm, video, GIF yoki matn yuborishingiz mumkin.\n"
        f"Bekor qilish: /cancel",
        reply_markup=get_cancel_inline(),
        parse_mode="Markdown"
    )
    await callback.answer()

# 2. Foydalanuvchi post yuborganda (rasm, video, gif, matn)
@router.message(PostState.waiting_for_content)
@router.message(F.photo | F.video | F.animation | F.document | (F.text & ~F.text.startswith("/")))
async def receive_post_content(message: Message, state: FSMContext):
    # Agar foydalanuvchi menyu tugmasini bosgan bo'lsa
    if message.text in ["📢 Mening kanallarim", "➕ Kanal qo'shish", "✍️ Post yuborish", "🕒 Kutilayotgan postlar", "📊 Bugungi hisobot", "ℹ️ Yordam"]:
        return

    user_id = message.from_user.id
    channels = await database.get_user_channels(user_id)
    
    if not channels:
        await message.answer(
            "⚠️ **Sizda hali birorta kanal ulanmagan!**\n"
            "Avval **➕ Kanal qo'shish** orqali kanalingizni ulang.",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
        await state.clear()
        return

    media_type = "text"
    file_id = None
    caption = None

    if message.photo:
        media_type = "photo"
        file_id = message.photo[-1].file_id
        caption = message.caption
    elif message.video:
        media_type = "video"
        file_id = message.video.file_id
        caption = message.caption
    elif message.animation:
        media_type = "animation"
        file_id = message.animation.file_id
        caption = message.caption
    elif message.document:
        media_type = "document"
        file_id = message.document.file_id
        caption = message.caption
    elif message.text:
        media_type = "text"
        caption = message.text

    # Holat ma'lumotlarini olish (preselected_channel bormi?)
    data = await state.get_data()
    preselected_id = data.get("preselected_channel_id")

    await state.update_data(
        media_type=media_type,
        file_id=file_id,
        caption=caption
    )

    if preselected_id:
        # Kanal allaqachon aniq tanlangan bo'lsa
        await state.update_data(target_channels=[preselected_id])
        await state.set_state(PostState.waiting_for_schedule_type)
        channel_info = await database.get_user_channel(user_id, preselected_id)
        ch_name = channel_info['title'] if channel_info else "Kanal"
        await message.answer(
            f"✅ Post qabul qilindi!\n"
            f"📢 Tanlangan kanal: **{ch_name}**\n\n"
            f"Postni qachon joylamoqchisiz?",
            reply_markup=get_post_schedule_inline(),
            parse_mode="Markdown"
        )
    else:
        # Foydalanuvchidan qaysi kanalga qo'yishni so'rash
        await state.set_state(PostState.waiting_for_target_channel)
        await message.answer(
            "✅ **Post qabul qilindi!**\n\n"
            "Ushbu postni qaysi kanalingizga joylashtirmoqchisiz?",
            reply_markup=get_post_target_channels_inline(channels),
            parse_mode="Markdown"
        )

# 3. Kanal tanlash callback
@router.callback_query(F.data.startswith("post_target_"))
async def callback_choose_target_channel(callback: CallbackQuery, state: FSMContext):
    target = callback.data.replace("post_target_", "")
    user_id = callback.from_user.id
    
    if target == "all":
        channels = await database.get_user_channels(user_id)
        target_channel_ids = [ch["channel_id"] for ch in channels]
        target_name = f"Barcha kanallar ({len(channels)} ta)"
    else:
        channel_id = int(target)
        ch = await database.get_user_channel(user_id, channel_id)
        if not ch:
            await callback.answer("⚠️ Kanal topilmadi!", show_alert=True)
            return
        target_channel_ids = [channel_id]
        target_name = ch["title"]

    await state.update_data(target_channels=target_channel_ids)
    await state.set_state(PostState.waiting_for_schedule_type)
    
    await callback.message.edit_text(
        f"📢 **Tanlangan kanal:** {target_name}\n\n"
        f"Endi postni joylash usulini tanlang:\n\n"
        f"⚡ **Hozir joylash:** Bir zumda kanalga chiqariladi.\n"
        f"🕒 **Faol vaqtda joylash (Smart Queue):** Kanalingiz auditoriyasi eng faol bo'lgan soatlarda avtomatik chiqariladi.\n"
        f"⏳ **Vaqtni belgilash:** O'zingiz xohlagan aniq soatni kiritasiz.",
        reply_markup=get_post_schedule_inline(),
        parse_mode="Markdown"
    )
    await callback.answer()

# 4. Joylash usuli: Hozir joylash
@router.callback_query(F.data == "post_publish_now")
async def callback_publish_now(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    target_channels = data.get("target_channels", [])
    media_type = data.get("media_type")
    file_id = data.get("file_id")
    caption = data.get("caption")
    user_id = callback.from_user.id

    if not target_channels:
        await callback.answer("⚠️ Xatolik: Kanal tanlanmagan!", show_alert=True)
        return

    await callback.message.edit_text("⏳ Post kanal(lar)ga joylanmoqda...")

    success_reports = []
    error_reports = []

    for ch_id in target_channels:
        ch = await database.get_user_channel(user_id, ch_id)
        ch_title = ch["title"] if ch else str(ch_id)
        ch_username = ch.get("username") if ch else None

        try:
            sent_msg = await publish_media_to_channel(bot, ch_id, media_type, file_id, caption)
            post_id = await database.save_post(
                user_id=user_id,
                channel_id=ch_id,
                media_type=media_type,
                file_id=file_id,
                caption=caption,
                status="published",
                message_id=sent_msg.message_id
            )
            link = get_post_url(ch_username, ch_id, sent_msg.message_id)
            success_reports.append(f"• **{ch_title}:** [Postni ko'rish]({link})")
        except TelegramAPIError as e:
            await database.save_post(
                user_id=user_id,
                channel_id=ch_id,
                media_type=media_type,
                file_id=file_id,
                caption=caption,
                status="failed"
            )
            error_reports.append(f"• **{ch_title}:** Xatolik ({e.message})")

    await state.clear()

    result_text = "🎉 **Natija:**\n\n"
    if success_reports:
        result_text += "✅ **Muvaffaqiyatli joylangan postlar:**\n" + "\n".join(success_reports) + "\n\n"
    if error_reports:
        result_text += "❌ **Joylanmagan kanallar:**\n" + "\n".join(error_reports)

    await callback.message.edit_text(result_text, reply_markup=None, parse_mode="Markdown")
    await callback.answer()

# 5. Joylash usuli: Faol vaqtda joylash (Smart Peak Hours Queue)
@router.callback_query(F.data == "post_publish_peak")
async def callback_publish_peak(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    target_channels = data.get("target_channels", [])
    media_type = data.get("media_type")
    file_id = data.get("file_id")
    caption = data.get("caption")
    user_id = callback.from_user.id

    if not target_channels:
        await callback.answer("⚠️ Kanal tanlanmagan!", show_alert=True)
        return

    peak_dt, label = calculate_next_peak_time()
    scheduled_str = peak_dt.strftime("%Y-%m-%d %H:%M:%S")
    display_time = peak_dt.strftime("%d.%m.%Y soat %H:%M")

    for ch_id in target_channels:
        await database.save_post(
            user_id=user_id,
            channel_id=ch_id,
            media_type=media_type,
            file_id=file_id,
            caption=caption,
            status="pending",
            scheduled_at=scheduled_str
        )

    await state.clear()

    await callback.message.edit_text(
        f"🎯 **Smart Queue (Faol vaqt) qabul qilindi!**\n\n"
        f"🕒 Rejalashtirilgan vaqt: **{display_time}** ({label})\n"
        f"📢 Kanallar soni: **{len(target_channels)} ta**\n\n"
        f"Bot ushbu vaqtda postni avtomatik ravishda kanalingizga chiqaradi va sizga xabar beradi. "
        f"Barcha kutilayotgan postlarni **🕒 Kutilayotgan postlar** menyusi orqali ko'rishingiz mumkin.",
        parse_mode="Markdown"
    )
    await callback.answer()

# 6. Joylash usuli: O'z vaqtini kiritish
@router.callback_query(F.data == "post_publish_custom")
async def callback_publish_custom(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PostState.waiting_for_custom_time)
    await callback.message.edit_text(
        "⏳ **Post qachon chiqishini xohlaysiz?**\n\n"
        "Iltimos, vaqtni quyidagi formatlardan birida yuboring:\n"
        "• Faqat soat: masalan `16:30` yoki `21:00` (bugungi kun uchun)\n"
        "• Sana va soat: masalan `25.11 15:00` yoki `2026-11-25 18:00`\n\n"
        "Bekor qilish uchun: /cancel",
        reply_markup=get_cancel_inline(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(PostState.waiting_for_custom_time)
async def process_custom_time(message: Message, state: FSMContext):
    text = message.text.strip()
    now = get_tz_now()
    tz = pytz.timezone(TIMEZONE)
    target_dt = None

    # 1. Format: HH:MM
    if re.match(r"^\d{1,2}:\d{2}$", text):
        parts = text.split(":")
        h, m = int(parts[0]), int(parts[1])
        if 0 <= h < 24 and 0 <= m < 60:
            target_dt = tz.localize(datetime(now.year, now.month, now.day, h, m, 0))
            if target_dt <= now:
                # Agar bugungi vaqt o'tgan bo'lsa, ertangi kunga o'tkazamiz
                target_dt += timedelta(days=1)

    # 2. Format: DD.MM HH:MM
    elif re.match(r"^\d{1,2}\.\d{1,2}\s+\d{1,2}:\d{2}$", text):
        try:
            date_part, time_part = text.split()
            d, month = map(int, date_part.split("."))
            h, m = map(int, time_part.split(":"))
            target_dt = tz.localize(datetime(now.year, month, d, h, m, 0))
        except Exception:
            target_dt = None

    # 3. Format: YYYY-MM-DD HH:MM
    elif re.match(r"^\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}$", text):
        try:
            target_dt = tz.localize(datetime.strptime(text, "%Y-%m-%d %H:%M"))
        except Exception:
            target_dt = None

    if not target_dt or target_dt <= now:
        await message.answer(
            "⚠️ Noto'g'ri vaqt formati yoki o'tib ketgan vaqt!\n"
            "Iltimos, kelgusi vaqtni kiriting (masalan: `18:45` yoki `25.11 12:00`)\n"
            "Bekor qilish uchun: /cancel",
            parse_mode="Markdown"
        )
        return

    data = await state.get_data()
    target_channels = data.get("target_channels", [])
    media_type = data.get("media_type")
    file_id = data.get("file_id")
    caption = data.get("caption")
    user_id = message.from_user.id

    scheduled_str = target_dt.strftime("%Y-%m-%d %H:%M:%S")
    display_time = target_dt.strftime("%d.%m.%Y soat %H:%M")

    for ch_id in target_channels:
        await database.save_post(
            user_id=user_id,
            channel_id=ch_id,
            media_type=media_type,
            file_id=file_id,
            caption=caption,
            status="pending",
            scheduled_at=scheduled_str
        )

    await state.clear()
    await message.answer(
        f"✅ **Postingiz muvaffaqiyatli rejalashtirildi!**\n\n"
        f"📅 Belgilangan vaqt: **{display_time}**\n"
        f"📢 Tanlangan kanallar: **{len(target_channels)} ta**\n\n"
        f"Belgilangan vaqtda bot postni kanalga chiqaradi.",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

# 7. Bekor qilish
@router.callback_query(F.data == "post_cancel")
async def callback_cancel_post(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Jarayon bekor qilindi.")
    await callback.answer()

# 8. Kutilayotgan postlar ro'yxatini ko'rish
@router.message(F.text == "🕒 Kutilayotgan postlar")
async def show_pending_posts(message: Message):
    user_id = message.from_user.id
    posts = await database.get_user_pending_posts(user_id)

    if not posts:
        await message.answer("🕒 Hozirda hech qanday kutilayotgan yoki rejalashtirilgan post yo'q.")
        return

    await message.answer(f"🕒 **Kutilayotgan postlaringiz ({len(posts)} ta):**\n")

    for p in posts:
        cap = p.get('caption') or "(Matnsiz media)"
        cap_preview = cap[:60] + "..." if len(cap) > 60 else cap
        text = (
            f"📌 **Kanal:** {p.get('channel_title', 'Kanal')}\n"
            f"📦 **Turi:** {p['media_type'].capitalize()}\n"
            f"⏰ **Vaqti:** {p.get('scheduled_at')}\n"
            f"💬 **Mazmuni:** {cap_preview}"
        )
        await message.answer(text, reply_markup=get_pending_post_item_inline(p["id"]), parse_mode="Markdown")

# 9. Kutilayotgan postni bekor qilish
@router.callback_query(F.data.startswith("del_pending_"))
async def callback_delete_pending(callback: CallbackQuery):
    post_id = int(callback.data.replace("del_pending_", ""))
    user_id = callback.from_user.id
    
    await database.delete_pending_post(post_id, user_id)
    await callback.message.edit_text("🗑 Ushbu rejalashtirilgan post bekor qilindi.")
    await callback.answer("O'chirildi!", show_alert=True)
