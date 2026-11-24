from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

import database
from keyboards import get_main_keyboard

router = Router()

START_TEXT = """
👋 **Assalomu alaykum, {name}!**

Ushbu bot orqali siz o'z Telegram kanallaringizni ulab, ularga postlarni oson va qulay boshqarishingiz mumkin:

✨ **Asosiy imkoniyatlar:**
1️⃣ **O'z kanallaringizni ulash:** Botni kanalingizga admin qilib qo'shasiz va botga ID yoki @username yuborasiz (yoki kanaldan xabar uzatasiz).
2️⃣ **Postlarni joylash:** Rasm, video, GIF yoki matnli postlarni yuborasiz — bot qaysi kanalga va qachon joylashni so'raydi.
3️⃣ **Smart Queue (Faol vaqtlarda joylash):** Postlarni auditoriya eng faol bo'lgan soatlarda avtomatik navbat bilan chiqarish.
4️⃣ **Kunlik 23:30 hisoboti:** Har kuni kechasi soat 23:30 da kanalingizga qo'yilgan postlar va obunachilar soni bo'yicha to'liq hisobot olasiz.
5️⃣ **Multi-user (Har kim o'z kanalini boshqaradi):** Har bir foydalanuvchi faqat o'zi ulagan kanallarni ko'radi va boshqaradi!

Boshlash uchun pastdagi **➕ Kanal qo'shish** tugmasini bosing!
"""

HELP_TEXT = """
📖 **Botdan foydalanish bo'yicha qo'llanma:**

1. **Kanal ulash tartibi:**
   • Avval botni o'z kanalingizga admin qilib tayinlang.
   • Admin huquqlarida **"Xabarlarni yuborish"** (Post messages) ruxsati yoqilgan bo'lishi shart!
   • Botdagi **➕ Kanal qo'shish** tugmasini bosing va kanalingiz @username'ini, ID'sini yuboring yoki kanaldan biror xabarni botga uzating (forward qiling).
   • Bot kanal a'zolarini va ma'lumotlarini tekshirib, tizimga saqlaydi.

2. **Post joylash:**
   • Istalgan vaqtda botga rasm, video, GIF yoki matn yuboring.
   • Bot qaysi kanalingizga joylashni so'raydi.
   • Joylash usulini tanlaysiz:
     - ⚡ **Hozir joylash:** Bir zumda kanalga chiqaradi.
     - 🕒 **Faol vaqtda joylash:** Eng yaqin faol soatda (09:00, 13:00, 18:30, 21:00) avtomatik chiqaradi.
     - ⏳ **Vaqtni belgilash:** O'zingiz belgilagan vaqtda joylaydi.

3. **Kunlik hisobot:**
   • Har kuni soat 23:30 da bot har bir kanalingiz bo'yicha kunlik hisobot yuboradi (obunachilar dinamikasi, qo'yilgan postlar ro'yxati).
   • Shuningdek, xohlagan paytingiz **📊 Bugungi hisobot** tugmasini bosib, joriy holatni ko'rishingiz mumkin.

❌ Amalni bekor qilish uchun: /cancel buyrug'ini yuboring.
"""

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    await database.upsert_user(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name
    )
    
    await message.answer(
        START_TEXT.format(name=user.first_name),
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@router.message(Command("help"))
@router.message(F.text == "ℹ️ Yordam")
async def cmd_help(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        HELP_TEXT,
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Hech qanday faol jarayon yo'q.", reply_markup=get_main_keyboard())
        return
    
    await state.clear()
    await message.answer("Jarayon bekor qilindi.", reply_markup=get_main_keyboard())
