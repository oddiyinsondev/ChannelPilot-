from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Asosiy menyu tugmalari"""
    keyboard = [
        [
            KeyboardButton(text="📢 Mening kanallarim"),
            KeyboardButton(text="➕ Kanal qo'shish")
        ],
        [
            KeyboardButton(text="✍️ Post yuborish"),
            KeyboardButton(text="🕒 Kutilayotgan postlar")
        ],
        [
            KeyboardButton(text="📊 Bugungi hisobot"),
            KeyboardButton(text="ℹ️ Yordam")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_channels_inline(channels: list) -> InlineKeyboardMarkup:
    """Ulangan kanallar ro'yxati inline tugmalari"""
    buttons = []
    for ch in channels:
        name = ch.get("title", "Kanal")
        ch_id = ch.get("channel_id")
        buttons.append([InlineKeyboardButton(text=f"📢 {name}", callback_data=f"ch_view_{ch_id}")])
    
    buttons.append([InlineKeyboardButton(text="➕ Yangi kanal qo'shish", callback_data="add_channel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_channel_details_inline(channel_id: int) -> InlineKeyboardMarkup:
    """Bitta kanal tafsilotlari inline tugmalari"""
    buttons = [
        [
            InlineKeyboardButton(text="✍️ Shu kanalga post yozish", callback_data=f"ch_post_{channel_id}"),
            InlineKeyboardButton(text="🔄 Yangilash", callback_data=f"ch_refresh_{channel_id}")
        ],
        [
            InlineKeyboardButton(text="🗑 Kanalni o'chirish", callback_data=f"ch_delete_{channel_id}"),
            InlineKeyboardButton(text="◀️ Kanallar ro'yxatiga", callback_data="ch_list")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_channel_delete_confirm_inline(channel_id: int) -> InlineKeyboardMarkup:
    """Kanalni o'chirishni tasdiqlash"""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Ha, o'chirilsin", callback_data=f"ch_delete_confirm_{channel_id}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"ch_view_{channel_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_post_target_channels_inline(channels: list) -> InlineKeyboardMarkup:
    """Postni qaysi kanalga joylashni tanlash inline tugmalari"""
    buttons = []
    for ch in channels:
        name = ch.get("title", "Kanal")
        ch_id = ch.get("channel_id")
        buttons.append([InlineKeyboardButton(text=f"📢 {name}", callback_data=f"post_target_{ch_id}")])
    
    if len(channels) > 1:
        buttons.append([InlineKeyboardButton(text="🚀 Barcha kanallarga yuborish", callback_data="post_target_all")])
    
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="post_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_post_schedule_inline() -> InlineKeyboardMarkup:
    """Postni qachon chiqarishni tanlash"""
    buttons = [
        [
            InlineKeyboardButton(text="⚡ Hozir joylash (Darhol)", callback_data="post_publish_now")
        ],
        [
            InlineKeyboardButton(text="🕒 Faol vaqtda joylash (Smart Queue)", callback_data="post_publish_peak")
        ],
        [
            InlineKeyboardButton(text="⏳ Vaqtni belgilash", callback_data="post_publish_custom")
        ],
        [
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="post_cancel")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_pending_post_item_inline(post_id: int) -> InlineKeyboardMarkup:
    """Kutilayotgan postni bekor qilish tugmasi"""
    buttons = [
        [
            InlineKeyboardButton(text="🗑 Bekor qilish (O'chirish)", callback_data=f"del_pending_{post_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_inline() -> InlineKeyboardMarkup:
    """Oddiy bekor qilish inline tugmasi"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="post_cancel")]
    ])
