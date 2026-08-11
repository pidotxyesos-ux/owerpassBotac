BOT_TOKEN = "8975688414:AAGUC6Ag9ADN_p7Tb0R9a8xsLEnsFHFkWZM"
LZT_TOKEN = "uBXEh_QLUl1ywDYvzbkMLkwgZ9dkYpWs"
ADMIN_ID = 8543473783
REVIEWS_CHANNEL_ID = -1004311525622

LZT_HEADERS = {"Authorization": f"Bearer {LZT_TOKEN}"}
LZT_API_BASE = "https://api.lzt.market"

REVIEWS_CHANNEL_LINK = "https://t.me/overpass_repa"

# ========== НАСТРОЙКИ MONOBANK ==========
MONOBANK_TOKEN = "usLyJCT_CNwaIfVUwtqi57ATlqpLPVxUltn6xrANZ2cc"
# =======================================

# ========== КОДОВОЕ СЛОВО ДЛЯ LOLZTEAM ==========
# Используется для подтверждения покупки на LolzTeam
LZT_CONFIRM_WORD = "Бадді"
# ================================================

PRICELIST = {
    "myanmar": {"name": "🇲🇲 Мьянма (+95)", "price": 30, "uah": 35, "stars": 40, "lzt_name": "myanmar"},
    "usa": {"name": "🇺🇲 США (+1)", "price": 45, "uah": 55, "stars": 65, "lzt_name": "usa"},
    "colombia": {"name": "🇨🇴 Колумбия (+57)", "price": 45, "uah": 55, "stars": 65, "lzt_name": "colombia"},
    "bangladesh": {"name": "🇧🇩 Бангладеш (+880)", "price": 45, "uah": 55, "stars": 65, "lzt_name": "bangladesh"},
    "honduras": {"name": "🇭🇳 Гондурас (+5041)", "price": 50, "uah": 65, "stars": 75, "lzt_name": "honduras"},
    "brazil": {"name": "🇧🇷 Бразилия (+55)", "price": 75, "uah": 85, "stars": 100, "lzt_name": "brazil"},
    "uzbekistan": {"name": "🇺🇿 Узбекистан (+998)", "price": 75, "uah": 85, "stars": 100, "lzt_name": "uzbekistan"},
    "thailand": {"name": "🇹🇭 Таиланд (+66)", "price": 80, "uah": 90, "stars": 100, "lzt_name": "thailand"},
    "united kingdom": {"name": "🇬🇧 Великобритания (+44)", "price": 120, "uah": 105, "stars": 115, "lzt_name": "united kingdom"},
    "ukraine": {"name": "🇺🇦 Украина (+380)", "price": 130, "uah": 130, "stars": 150, "lzt_name": "ukraine"},
    "belarus": {"name": "🇧🇾 Беларусь (+375)", "price": 150, "uah": 175, "stars": 200, "lzt_name": "belarus"},
    "kazakhstan": {"name": "🇰🇿 Казахстан (+7)", "price": 160, "uah": 175, "stars": 200, "lzt_name": "kazakhstan"},
    "poland": {"name": "🇵🇱 Польша (+48)", "price": 170, "uah": 200, "stars": 225, "lzt_name": "poland"},
    "russia": {"name": "🇷🇺 Россия (+7)", "price": 240, "uah": 220, "stars": 250, "lzt_name": "russia"},
    "germany": {"name": "🇩🇪 Германия (+49)", "price": 250, "uah": 265, "stars": 300, "lzt_name": "germany"},
}

# ========== ТЕСТОВЫЙ ТОВАР (TikTok куки) ==========
# Это не тестовый товар, а реальная покупка TikTok куки на LolzTeam
TEST_PRICELIST = {
    "test": {"name": "🎵 TikTok Cookie", "price": 1, "uah": 1, "stars": 1, "lzt_name": "test"},
}
# ==================================================

PREMIUM_PRICELIST = {
    "usa": {"name": "🇺🇲 США (+1) [Premium]", "price": 120, "uah": 135, "stars": 150, "lzt_name": "usa"},
    "canada": {"name": "🇨🇦 Канада (+1) [Premium]", "price": 120, "uah": 135, "stars": 150, "lzt_name": "canada"},
    "uzbekistan": {"name": "🇺🇿 Узбекистан (+998) [Premium]", "price": 350, "uah": 360, "stars": 400, "lzt_name": "uzbekistan"},
    "ukraine": {"name": "🇺🇦 Украина (+380) [Premium]", "price": 350, "uah": 360, "stars": 400, "lzt_name": "ukraine"},
    "germany": {"name": "🇩🇪 Германия (+49) [Premium]", "price": 400, "uah": 450, "stars": 500, "lzt_name": "germany"},
}

TIKTOK_PRICES = {
    "regular": {"name": "🎵 TikTok (Обычный)", "price": 50, "uah": 55, "stars": 65, "category": "tiktok", "params": {}},
    "live": {
        "name": "🔥 TikTok (С LIVE эфирами)",
        "price": 240,
        "uah": 265,
        "stars": 300,
        "category": "tiktok",
        "params": {"hasLivePermission": 1},
    },
}

DISCORD_PRICES = {
    "regular": {"name": "🎮 Discord (Авторег)", "price": 40, "uah": 45, "stars": 50, "category": "discord", "params": {}},
    "nitro": {"name": "✨ Discord (С Nitro)", "price": 150, "uah": 175, "stars": 200, "category": "discord", "params": {"nitro": 1}},
}

def format_price_label(item: dict) -> str:
    return f"{item['uah']} ₴ / {item['stars']} ⭐"

USERNAMES = [
    {"username": "@bezsmertniu", "tag": "NEW", "price_usd": 5.0, "stars": 500},
    {"username": "@soyznikow", "tag": "NEW", "price_usd": 4.0, "stars": 400},
    {"username": "@nenavistnikow", "tag": "", "price_usd": 4.0, "stars": 400},
    {"username": "@argentow", "tag": "NEW", "price_usd": 3.0, "stars": 300},
    {"username": "@obezbashenni", "tag": "", "price_usd": 3.0, "stars": 200},
    {"username": "@razbogatewshiy", "tag": "", "price_usd": 2.0, "stars": 150},
    {"username": "@Melstroynost777", "tag": "", "price_usd": 1.5, "stars": 100},
]