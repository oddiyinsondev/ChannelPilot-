from aiogram import Router, F, Bot
from aiogram.types import Message

import database
from keyboards import get_main_keyboard
from scheduler import format_channel_report, get_tz_now

router = Router()

@router.message(F.text == "📊 Bugungi hisobot")
async def show_today_report(message: Message, bot: Bot):
    user_id = message.from_user.id
    channels = await database.get_user_channels(user_id)

    if not channels:
        await message.answer(
            "⚠️ **Sizda hali birorta kanal ulanmagan!**\n\n"
            "Hisobot olish uchun avval **➕ Kanal qo'shish** orqali kanalingizni ulang.",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
        return

    wait_msg = await message.answer("🔄 Kanallar statistikasi to'planmoqda, bir oz kuting...")

    now_dt = get_tz_now()
    now_str = now_dt.strftime("%d-%m-%Y, soat %H:%M")

    report_header = (
        f"📊 **BUGUNGI KANAL HISOBOTI (Joriy holat)**\n"
        f"📅 **Vaqt:** {now_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    channel_reports = []
    for ch in channels:
        ch_text = await format_channel_report(bot, ch)
        channel_reports.append(ch_text)

    full_report = report_header + "\n━━━━━━━━━━━━━━━━━━━━━\n\n".join(channel_reports)
    full_report += (
        f"\n\n⏰ *Eslatma: Har kuni kechasi soat 23:30 da ushbu hisobot avtomatik ravishda yuboriladi.*"
    )

    await wait_msg.edit_text(full_report, parse_mode="Markdown")
