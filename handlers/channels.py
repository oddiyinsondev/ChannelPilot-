from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramAPIError

import database
from states import AddChannelState
from keyboards import (
    get_main_keyboard,
    get_channels_inline,
    get_channel_details_inline,
    get_channel_delete_confirm_inline,
)

router = Router()

ADD_CHANNEL_INSTRUCTION = """
➕ **Kanalni botga ulash bo'yicha yo'riqnoma:**

1️⃣ Avval botimizni o'z kanalingizga qo'shing va uni **ADMIN** qilib tayinlang.
⚠️ *Muhim:* Admin huquqlarida **"Xabarlarni yuborish"** (Post messages) ruxsati yoqilgan bo'lishi kerak!

2️⃣ So'ngra quyidagi usullardan biri orqali kanalni yuboring:
• Kanal @username'ini yuboring (masalan: `@mening_kanalim`)
• Yoki kanal ID'sini yuboring (masalan: `-1001234567890`)
• **Yoki kanalingizdan istalgan bir xabarni shu yerga FORWARD (uzatish) qiling!**

❌ Bekor qilish uchun: /cancel
"""

@router.message(F.text == "➕ Kanal qo'shish")
@router.callback_query(F.data == "add_channel")
async def start_add_channel(event: Message | CallbackQuery, state: FSMContext):
    await state.set_state(AddChannelState.waiting_for_channel)
    text = ADD_CHANNEL_INSTRUCTION
    
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.answer(text, parse_mode="Markdown")
    else:
        await event.answer(text, parse_mode="Markdown")

@router.message(AddChannelState.waiting_for_channel)
async def process_channel_input(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    target_chat_id = None
    
    # 1. Forward qilingan xabarni tekshiramiz
    if message.forward_from_chat:
        target_chat_id = message.forward_from_chat.id
    elif message.text:
        text = message.text.strip()
        if text.startswith("/cancel"):
            await state.clear()
            await message.answer("Kanal qo'shish bekor qilindi.", reply_markup=get_main_keyboard())
            return
        
        # ID yoki username
        try:
            if text.startswith("-100") or (text.startswith("-") and text[1:].isdigit()) or text.isdigit():
                target_chat_id = int(text)
            elif text.startswith("@"):
                target_chat_id = text
            else:
                target_chat_id = f"@{text}"
        except Exception:
            target_chat_id = text

    if not target_chat_id:
        await message.answer(
            "⚠️ Kanal aniqlanmadi. Iltimos, kanal @username'ini, ID'sini yuboring yoki kanaldan xabarni FORWARD qiling.\nBekor qilish uchun: /cancel"
        )
        return

    wait_msg = await message.answer("🔄 Kanal tekshirilmoqda, iltimos kuting...")

    try:
        # Kanal ma'lumotlarini olish
        chat = await bot.get_chat(target_chat_id)
        
        if chat.type != "channel":
            await wait_msg.edit_text(
                "⚠️ Bu kanal emas! Bot faqat Telegram kanallar bilan ishlaydi. Iltimos, kanalingizni yuboring."
            )
            return

        # Botning adminlik holatini tekshirish
        bot_user = await bot.get_me()
        bot_member = await bot.get_chat_member(chat.id, bot_user.id)
        
        is_admin = bot_member.status in ["administrator", "creator"]
        can_post = True
        
        if bot_member.status == "administrator":
            can_post = getattr(bot_member, "can_post_messages", False)

        if not is_admin:
            await wait_msg.edit_text(
                f"❌ **Bot kanalda admin emas!**\n\n"
                f"Kanal: **{chat.title}**\n"
                f"Iltimos, avval botni kanalingizga admin qiling va qaytadan yuboring.",
                parse_mode="Markdown"
            )
            return

        if not can_post:
            await wait_msg.edit_text(
                f"⚠️ **Ruxsat yetarli emas!**\n\n"
                f"Bot **{chat.title}** kanaliga admin qilingan, ammo **'Xabarlarni yuborish'** (Post messages) ruxsati berilmagan.\n"
                f"Kanal sozlamalariga kirib, botga xabar yozish ruxsatini yoqing va qaytadan yuboring.",
                parse_mode="Markdown"
            )
            return

        # Obunachilar sonini olish
        try:
            member_count = await bot.get_chat_member_count(chat.id)
        except Exception:
            member_count = 0

        invite_link = chat.invite_link or (f"https://t.me/{chat.username}" if chat.username else None)

        # Bazaga saqlash
        await database.add_or_update_channel(
            user_id=user_id,
            channel_id=chat.id,
            title=chat.title,
            username=chat.username,
            invite_link=invite_link,
            member_count=member_count
        )

        await state.clear()
        
        username_str = f"@{chat.username}" if chat.username else "Mavjud emas (Yopiq kanal)"
        success_text = (
            f"✅ **Kanal muvaffaqiyatli ulandi!**\n\n"
            f"📢 **Nomi:** {chat.title}\n"
            f"🔗 **Username:** {username_str}\n"
            f"🆔 **Kanal ID:** `{chat.id}`\n"
            f"👥 **Obunachilar soni:** {member_count:,} ta\n\n"
            f"Endi siz ushbu kanalga xohlagan vaqtingizda postlar yuborishingiz va kunlik hisobotlarni olishingiz mumkin!"
        )

        await wait_msg.edit_text(success_text, parse_mode="Markdown")

    except TelegramAPIError as e:
        await wait_msg.edit_text(
            f"❌ **Xatolik yuz berdi:** {e.message}\n\n"
            f"Ehtimol, bot kanalga qo'shilmagan yoki kanal topilmadi. Avval botni kanalingizga admin qilib qo'shing va qayta urinib ko'ring.\n"
            f"Bekor qilish uchun: /cancel",
            parse_mode="Markdown"
        )
    except Exception as e:
        await wait_msg.edit_text(
            f"❌ Kutilmagan xatolik: {str(e)}\nIltimos, qaytadan urinib ko'ring yoki /cancel bosing."
        )

@router.message(F.text == "📢 Mening kanallarim")
async def show_user_channels(message: Message):
    user_id = message.from_user.id
    channels = await database.get_user_channels(user_id)
    
    if not channels:
        await message.answer(
            "📋 **Sizda hali birorta kanal ulanmagan.**\n\n"
            "Kanal ulash uchun pastdagi **➕ Kanal qo'shish** tugmasini bosing.",
            reply_markup=get_channels_inline([]),
            parse_mode="Markdown"
        )
        return

    text = f"📋 **Sizning ulangan kanallaringiz ({len(channels)} ta):**\n\n"
    for i, ch in enumerate(channels, 1):
        uname = f"@{ch['username']}" if ch.get('username') else "Yopiq kanal"
        text += f"{i}. **{ch['title']}** ({uname}) — 👥 {ch.get('member_count', 0):,} ta a'zo\n"
    
    text += "\nBatafsil ma'lumot va boshqarish uchun pastdagi kerakli kanal tugmasini bosing:"
    await message.answer(text, reply_markup=get_channels_inline(channels), parse_mode="Markdown")

@router.callback_query(F.data == "ch_list")
async def callback_show_channels_list(callback: CallbackQuery):
    user_id = callback.from_user.id
    channels = await database.get_user_channels(user_id)
    
    if not channels:
        await callback.message.edit_text(
            "📋 **Sizda hali birorta kanal ulanmagan.**",
            reply_markup=get_channels_inline([]),
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    text = f"📋 **Sizning ulangan kanallaringiz ({len(channels)} ta):**\n\n"
    for i, ch in enumerate(channels, 1):
        uname = f"@{ch['username']}" if ch.get('username') else "Yopiq kanal"
        text += f"{i}. **{ch['title']}** ({uname}) — 👥 {ch.get('member_count', 0):,} ta a'zo\n"
    
    text += "\nBoshqarish uchun kanalni tanlang:"
    await callback.message.edit_text(text, reply_markup=get_channels_inline(channels), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("ch_view_"))
async def callback_view_channel(callback: CallbackQuery, bot: Bot):
    channel_id = int(callback.data.replace("ch_view_", ""))
    user_id = callback.from_user.id
    
    channel = await database.get_user_channel(user_id, channel_id)
    if not channel:
        await callback.answer("⚠️ Kanal topilmadi yoki sizga tegishli emas!", show_alert=True)
        return

    # Bugungi postlarni hisoblash
    today_posts = await database.get_today_posts_for_channel(channel_id)
    uname = f"@{channel['username']}" if channel.get('username') else "Yopiq kanal"
    
    text = (
        f"📢 **Kanal ma'lumotlari:**\n\n"
        f"📌 **Nomi:** {channel['title']}\n"
        f"🔗 **Username:** {uname}\n"
        f"🆔 **ID:** `{channel['channel_id']}`\n"
        f"👥 **Jami a'zolar:** {channel.get('member_count', 0):,} ta\n"
        f"📝 **Bugun qo'yilgan postlar:** {len(today_posts)} ta\n"
        f"📅 **Ulangan sana:** {channel.get('added_at', '')[:16]}\n"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_channel_details_inline(channel_id),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("ch_refresh_"))
async def callback_refresh_channel(callback: CallbackQuery, bot: Bot):
    channel_id = int(callback.data.replace("ch_refresh_", ""))
    user_id = callback.from_user.id
    
    channel = await database.get_user_channel(user_id, channel_id)
    if not channel:
        await callback.answer("⚠️ Kanal topilmadi!", show_alert=True)
        return

    try:
        member_count = await bot.get_chat_member_count(channel_id)
        chat = await bot.get_chat(channel_id)
        
        await database.add_or_update_channel(
            user_id=user_id,
            channel_id=channel_id,
            title=chat.title,
            username=chat.username,
            invite_link=chat.invite_link,
            member_count=member_count
        )
        
        await callback.answer("✅ Kanal ma'lumotlari va a'zolar soni yangilandi!", show_alert=True)
        # Sahifani qayta chizamiz
        today_posts = await database.get_today_posts_for_channel(channel_id)
        uname = f"@{chat.username}" if chat.username else "Yopiq kanal"
        
        text = (
            f"📢 **Kanal ma'lumotlari (Yangilandi):**\n\n"
            f"📌 **Nomi:** {chat.title}\n"
            f"🔗 **Username:** {uname}\n"
            f"🆔 **ID:** `{chat.id}`\n"
            f"👥 **Jami a'zolar:** {member_count:,} ta\n"
            f"📝 **Bugun qo'yilgan postlar:** {len(today_posts)} ta\n"
            f"📅 **Ulangan sana:** {channel.get('added_at', '')[:16]}\n"
        )
        await callback.message.edit_text(
            text,
            reply_markup=get_channel_details_inline(channel_id),
            parse_mode="Markdown"
        )
    except Exception as e:
        await callback.answer(f"Xatolik: {str(e)}", show_alert=True)

@router.callback_query(F.data.startswith("ch_delete_"))
async def callback_delete_channel_prompt(callback: CallbackQuery):
    if callback.data.startswith("ch_delete_confirm_"):
        return
    channel_id = int(callback.data.replace("ch_delete_", ""))
    await callback.message.edit_text(
        "⚠️ **Haqiqatdan ham ushbu kanalni botdan o'chirmoqchimisiz?**\n\n"
        "Kanal o'chirilsa, bot ushbu kanalga postlar joylamaydi va hisobotlar bermaydi.",
        reply_markup=get_channel_delete_confirm_inline(channel_id),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("ch_delete_confirm_"))
async def callback_delete_channel_confirm(callback: CallbackQuery):
    channel_id = int(callback.data.replace("ch_delete_confirm_", ""))
    user_id = callback.from_user.id
    
    await database.delete_user_channel(user_id, channel_id)
    await callback.answer("✅ Kanal muvaffaqiyatli o'chirildi!", show_alert=True)
    
    channels = await database.get_user_channels(user_id)
    if channels:
        text = f"📋 **Sizning ulangan kanallaringiz ({len(channels)} ta):**\n\n"
        for i, ch in enumerate(channels, 1):
            uname = f"@{ch['username']}" if ch.get('username') else "Yopiq kanal"
            text += f"{i}. **{ch['title']}** ({uname}) — 👥 {ch.get('member_count', 0):,} ta a'zo\n"
        await callback.message.edit_text(text, reply_markup=get_channels_inline(channels), parse_mode="Markdown")
    else:
        await callback.message.edit_text(
            "📋 Sizda hali birorta kanal ulanmagan.",
            reply_markup=get_channels_inline([]),
            parse_mode="Markdown"
        )
