# ChannelPilot-

Telegram kanallarni ulash, postlarni boshqarish, auditoriya faol bo'lgan paytlarda smart navbat bilan chiqarish hamda har kuni kechasi soat **23:30 da avtomatik kunlik hisobot** beruvchi to'liq avtonom Telegram bot.

---

## 🌟 Asosiy Imkoniyatlar

1. **Multi-User (Har kim o'z kanalini boshqaradi, markaziy adminka kerak emas):**
   - Har bir foydalanuvchi botga kirib (`/start`), o'zining bir yoki bir nechta kanallarini mustaqil ulay oladi.
   - Foydalanuvchilar bir-birining kanallarini ko'rmaydi va faqat o'z kanallariga post yubora oladi.

2. **Kanal ulash va tekshirish:**
   - Botni kanalga qo'shib, unga **Admin** huquqlarini (Post messages ruxsatini) berish yetarli.
   - Botga kanal @username'ini, ID'sini yuborish yoki shunchaki kanaldan biror xabarni **FORWARD** qilish orqali ulanadi.
   - Bot kanal a'zolari soni, nomi, havolasini tekshiradi va to'liq ma'lumot beradi.

3. **Postlarni joylash (Rasm, Video, GIF, Matn):**
   - Istalgan vaqtda botga media (caption bilan) yoki matn yuboriladi.
   - Bot qaysi kanalga joylashtirishni (yoki "Barcha kanallarga") so'raydi.
   - **Joylash usullari:**
     - ⚡ **Hozir joylash (Darhol):** Kanalga bir zumda post chiqaradi.
     - 🕒 **Faol vaqtda joylash (Smart Queue):** Auditoriya eng faol bo'ladigan eng yaqin soatlarda (09:00, 13:00, 18:30, 21:00) avtomatik chiqaradi.
     - ⏳ **Vaqtni belgilash:** Foydalanuvchi o'zi istagan vaqtni (masalan: `16:30` yoki `25.11 12:00`) belgilaydi.

4. **Kunlik 23:30 Hisoboti (Avtomatik):**
   - Har kuni soat **23:30 da** bot avtomatik ravishda har bir kanal egasiga o'zining kanallari bo'yicha hisobot yuboradi:
     - 👥 Jami a'zolar soni va kunlik o'sish dinamikasi (`+15 ta 📈` yoki `-2 ta 📉`).
     - 📝 Bugun kanalga joylangan postlar soni va ro'yxati (vaqti, post turi, post havolasi bilan).
   - Foydalanuvchi istalgan vaqtda **"📊 Bugungi hisobot"** tugmasi orqali joriy holatni ko'ra oladi.

5. **Kutilayotgan postlar boshqaruvi:**
   - Rejalashtirilgan postlarni ko'rish va xohlagan paytda bekor qilish imkoniyati.

---

## 📁 Loyiha Tuzilmasi

```
d:\Kanallar bilan ishlovchi bot\
├── bot.py                # Asosiy ishga tushirish fayli
├── config.py             # Sozlamalar va o'zgaruvchilar
├── database.py           # SQLite asinxron ma'lumotlar bazasi
├── scheduler.py          # APScheduler (23:30 hisobot va postlar navbati)
├── states.py             # Aiogram FSM holatlari
├── keyboards.py          # Reply va Inline tugmalar
├── handlers/
│   ├── start.py          # /start, /help, /cancel komandalari
│   ├── channels.py       # Kanal qo'shish, ro'yxat, yangilash, o'chirish
│   ├── post.py           # Post qabul qilish, kanal tanlash, rejalashtirish
│   └── report.py         # Jonli (on-demand) hisobot tugmasi
├── requirements.txt      # Kerakli Python kutubxonalari
├── test_bot.py           # Tizim sinov testi
├── .env.example          # Sozlamalar namunasi
└── .env                  # Bot token va sozlamalar fayli
```

---

## 🚀 O'rnatish va Ishga Tushirish

### 1-qadam: Kerakli kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

### 2-qadam: Bot Tokenni kiritish
1. Telegramda [@BotFather](https://t.me/BotFather) orqali yangi bot yarating va `API Token`ni oling.
2. `.env` faylini ochib, tokeningizni kiriting:
```ini
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TIMEZONE=Asia/Tashkent
DAILY_REPORT_TIME=23:30
```

### 3-qadam: Botni ishga tushirish
```bash
python bot.py
```

---

## 📱 Botdan Foydalanish Tartibi

1. Telegramda botingizga `/start` buyrug'ini bering.
2. Botingizni o'z Telegram kanalingizga **Admin** qilib qo'shing va **"Xabarlarni yuborish"** (Post messages) ruxsatini bering.
3. Botda **"➕ Kanal qo'shish"** tugmasini bosing:
   - Kanalingiz @username'ini (masalan: `@mening_kanalim`), yoki
   - Kanal ID'sini (masalan: `-1001234567890`), yoki
   - Kanaldan istalgan bir xabarni botga **Forward** (uzatish) qiling.
4. Bot kanalni tekshiradi, a'zolar sonini ko'rsatadi va tizimga ulaydi.
5. Endi botga rasm, video, GIF yoki matn yuboring — bot qaysi kanalga va qachon joylashni so'raydi.
6. Har kuni kechasi soat **23:30 da** kanalingiz bo'yicha to'liq hisobot avtomatik tarzda sizga keladi!
