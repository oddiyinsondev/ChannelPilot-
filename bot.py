import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, DAILY_REPORT_HOUR, DAILY_REPORT_MINUTE, TIMEZONE
import database
from scheduler import setup_scheduler
from handlers import start, channels, post, report

# Log sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ChannelBot")

async def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ BOT_TOKEN belgilanmagan! Iltimos, .env fayliga @BotFather dan olingan bot tokenni yozing.")
        print("\n" + "="*60)
        print("DIQQAT: .env faylida BOT_TOKEN ko'rsatilmagan!")
        print("Iltimos, .env faylini oching va bot tokeningizni kiriting:")
        print("BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
        print("="*60 + "\n")
        return

    # Ma'lumotlar bazasini ishga tushirish
    await database.init_db()
    logger.info("Ma'lumotlar bazasi tayyor.")

    # Bot va Dispatcher obyektlari
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Routerni ulash
    dp.include_router(start.router)
    dp.include_router(channels.router)
    dp.include_router(post.router)
    dp.include_router(report.router)

    # Rejalashtiruvchi (Scheduler) ni ishga tushirish
    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info(f"Rejalashtiruvchi ishga tushdi. Kunlik hisobot: soat {DAILY_REPORT_HOUR:02d}:{DAILY_REPORT_MINUTE:02d} ({TIMEZONE})")

    # Bot ma'lumotlarini olish
    try:
        bot_user = await bot.get_me()
        logger.info(f"Bot muvaffaqiyatli ishga tushdi: @{bot_user.username} ({bot_user.full_name})")
    except Exception as e:
        logger.error(f"Botga ulanishda xatolik: {e}")
        return

    # Eski kutilmagan xabarlarni tozalash va polling boshlash
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot xabarlarni qabul qilishga tayyor...")

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()
        logger.info("Bot to'xtatildi.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Dastur to'xtatildi.")
