import asyncio
import os
import database
from handlers.post import calculate_next_peak_time

async def run_tests():
    print("--- 1. Baza initsializatsiyasi ---")
    await database.init_db()
    print("✅ init_db() muvaffaqiyatli")

    print("\n--- 2. Multi-user va kanal ajratilishi testi ---")
    # 2 ta har xil foydalanuvchi
    user1_id = 11111111
    user2_id = 22222222

    await database.upsert_user(user1_id, "ali_user", "Ali Valiyev")
    await database.upsert_user(user2_id, "vali_user", "Vali Aliyev")

    # User 1 ikkita kanal qo'shadi
    await database.add_or_update_channel(
        user_id=user1_id,
        channel_id=-1001111111,
        title="Ali Kanal 1",
        username="ali_kanal1",
        invite_link="https://t.me/ali_kanal1",
        member_count=1500
    )
    await database.add_or_update_channel(
        user_id=user1_id,
        channel_id=-1001111112,
        title="Ali Kanal 2",
        username="ali_kanal2",
        invite_link="https://t.me/ali_kanal2",
        member_count=3200
    )

    # User 2 bitta kanal qo'shadi
    await database.add_or_update_channel(
        user_id=user2_id,
        channel_id=-1002222222,
        title="Vali Kanal",
        username="vali_kanal",
        invite_link="https://t.me/vali_kanal",
        member_count=500
    )

    # User 1 kanallarini tekshirish
    u1_channels = await database.get_user_channels(user1_id)
    assert len(u1_channels) == 2, f"Kutilgan 2 ta kanal, olindi: {len(u1_channels)}"
    print(f"✅ User 1 kanallari to'g'ri olindi: {[c['title'] for c in u1_channels]}")

    # User 2 faqat o'z kanalini ko'rishini tekshirish (Izolyatsiya)
    u2_channels = await database.get_user_channels(user2_id)
    assert len(u2_channels) == 1, f"Kutilgan 1 ta kanal, olindi: {len(u2_channels)}"
    assert u2_channels[0]["channel_id"] == -1002222222
    print(f"✅ User 2 faqat o'z kanalini ko'rmoqda: {[c['title'] for c in u2_channels]}")

    print("\n--- 3. Post yaratish va navbat testi ---")
    # Post yaratish (darhol)
    post1_id = await database.save_post(
        user_id=user1_id,
        channel_id=-1001111111,
        media_type="photo",
        file_id="AgACAgIAAxkBAAI...",
        caption="Ajoyib foto post!",
        status="published",
        message_id=45
    )
    print(f"✅ Chop etilgan post yaratildi: ID {post1_id}")

    # Post yaratish (rejalashtirilgan)
    post2_id = await database.save_post(
        user_id=user1_id,
        channel_id=-1001111112,
        media_type="video",
        file_id="BAACAgIAAxkBAAI...",
        caption="Kechki video darslik",
        status="pending",
        scheduled_at="2026-11-24 18:30:00"
    )
    print(f"✅ Rejalashtirilgan post yaratildi: ID {post2_id}")

    # Kutilayotgan postlar
    pending = await database.get_user_pending_posts(user1_id)
    assert len(pending) == 1
    assert pending[0]["id"] == post2_id
    print(f"✅ User 1 kutilayotgan postlari: {len(pending)} ta")

    # Bugungi postlar
    today_posts = await database.get_today_posts_for_channel(-1001111111)
    assert len(today_posts) == 1
    assert today_posts[0]["caption"] == "Ajoyib foto post!"
    print(f"✅ Bugungi kanal postlari ro'yxati to'g'ri: {len(today_posts)} ta post")

    print("\n--- 4. Smart Peak Time hisoblash testi ---")
    next_peak, label = calculate_next_peak_time()
    print(f"✅ Keyingi faol soat: {next_peak.strftime('%Y-%m-%d %H:%M')} ({label})")

    print("\n🎉 Barcha testlar muvaffaqiyatli yakunlandi!")

if __name__ == "__main__":
    asyncio.run(run_tests())
