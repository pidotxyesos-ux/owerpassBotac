import asyncio
import logging
import json
import os
import sys
import hashlib
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = "8975688414:AAGUC6Ag9ADN_p7Tb0R9a8xsLEnsFHFkWZM"
ADMIN_ID = 8543473783
CHANNEL_ID = "-1004311525622"
STORE_CHANNEL_ID = "-1004292126045"

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# ==================== PREMIUM EMOJI IDS ====================
EMOJI = {
    "star": "5438496463044752972",       # Звезда
    "check": "5206607081334906820",      # Галочка
    "fire": "5424972470023104089",       # Огонь
    "money": "5287231198098117669",      # Деньги
    "cart": "5312361253610475399",       # Корзина
    "user": "5190872550250405805",       # Пользователь
    "gift": "5278467510604160626",       # Подарок
    "time": "5382194935057372936",       # Время
    "warn": "5274099962655816924",       # Восклицание
}

def p_emoji(key: str) -> str:
    """Возвращает HTML тег премиум эмодзи"""
    emoji_id = EMOJI.get(key)
    if not emoji_id:
        return ""
    return f"<tg-emoji emoji-id='{emoji_id}'> </tg-emoji>"

# ==================== ФАЙЛЫ ====================
ORDERS_FILE = "orders.json"
REVIEWS_FILE = "reviews.json"
RELAY_FILE = "relay_map.json"
REQUISITES_FILE = "requisites.json"
USERS_FILE = "users.json"
REFERRALS_FILE = "referrals.json"
PROMO_CODES_FILE = "promo_codes.json"
PROMOTIONS_FILE = "promotions.json"
BROADCASTS_FILE = "broadcasts.json"
TRAFFIC_SOURCES_FILE = "traffic_sources.json"
SETTINGS_FILE = "settings.json"
ORDER_COUNTER_FILE = "order_counter.json"
CHAT_HISTORY_FILE = "chat_history.json"
PROMO_EARNINGS_FILE = "promo_earnings.json" # Статистика заработка промокодов

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_orders(): return load_json(ORDERS_FILE)
def save_orders(o): save_json(ORDERS_FILE, o)
def load_reviews(): return load_json(REVIEWS_FILE)
def save_reviews(r): save_json(REVIEWS_FILE, r)
def load_relay(): return load_json(RELAY_FILE)
def save_relay(r): save_json(RELAY_FILE, r)
def load_requisites(): return load_json(REQUISITES_FILE)
def save_requisites(r): save_json(REQUISITES_FILE, r)
def load_users(): return load_json(USERS_FILE)
def save_users(u): save_json(USERS_FILE, u)
def load_referrals(): return load_json(REFERRALS_FILE)
def save_referrals(r): save_json(REFERRALS_FILE, r)
def load_promo_codes(): return load_json(PROMO_CODES_FILE)
def save_promo_codes(p): save_json(PROMO_CODES_FILE, p)
def load_promotions(): return load_json(PROMOTIONS_FILE)
def save_promotions(p): save_json(PROMOTIONS_FILE, p)
def load_broadcasts(): return load_json(BROADCASTS_FILE)
def save_broadcasts(b): save_json(BROADCASTS_FILE, b)
def load_traffic_sources(): return load_json(TRAFFIC_SOURCES_FILE)
def save_traffic_sources(t): save_json(TRAFFIC_SOURCES_FILE, t)
def load_settings(): return load_json(SETTINGS_FILE)
def save_settings(s): save_json(SETTINGS_FILE, s)
def load_order_counter(): return load_json(ORDER_COUNTER_FILE)
def save_order_counter(c): save_json(ORDER_COUNTER_FILE, c)
def load_chat_history(): return load_json(CHAT_HISTORY_FILE)
def save_chat_history(c): save_json(CHAT_HISTORY_FILE, c)
def load_promo_earnings(): return load_json(PROMO_EARNINGS_FILE)
def save_promo_earnings(e): save_json(PROMO_EARNINGS_FILE, e)

# ==================== НАСТРОЙКИ ====================
DEFAULT_SETTINGS = {
    "referral_bonus_percent": 5.0,
    "promo_owner_commission_percent": 20.0, # Процент комиссии владельцу промокода
    "level_bronze_min": 0,
    "level_bronze_discount": 0,
    "level_silver_min": 500,
    "level_silver_discount": 3,
    "level_gold_min": 1500,
    "level_gold_discount": 5,
    "level_platinum_min": 3000,
    "level_platinum_discount": 7,
    "level_vip_min": 5000,
    "level_vip_discount": 10,
}

if not os.path.exists(SETTINGS_FILE):
    save_settings(DEFAULT_SETTINGS)

def get_setting(key, default=None):
    settings = load_settings()
    return settings.get(key, DEFAULT_SETTINGS.get(key, default))

LEVEL_KEYS = {
    "bronze": "Бронза",
    "silver": "Серебро",
    "gold": "Золото",
    "platinum": "Платина",
    "vip": "VIP",
}

# ==================== ПОЛЬЗОВАТЕЛИ ====================
async def add_user(user_id: int, username: str = None, full_name: str = None, ref_code: str = None):
    users = load_users()
    referrals = load_referrals()
    user_key = str(user_id)
    is_new = user_key not in users
    
    if is_new:
        users[user_key] = {
            "user_id": user_id,
            "username": username,
            "full_name": full_name,
            "first_seen": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "referred_by": None,
            "referral_code": None,
            "total_spent": 0.0,
            "orders_count": 0,
            "traffic_source": None,
        }
        
        if ref_code and ref_code.startswith("ref_"):
            actual_ref_code = ref_code[4:]
            for referrer_id, ref_data in referrals.items():
                if ref_data.get("referral_code") == actual_ref_code:
                    users[user_key]["referred_by"] = int(referrer_id)
                    if "referrals_list" not in ref_data:
                        ref_data["referrals_list"] = []
                    ref_data["referrals_list"].append({
                        "user_id": user_id,
                        "username": username,
                        "date": datetime.now().isoformat(),
                        "first_purchase_done": False,
                    })
                    break
        
        if ref_code and not ref_code.startswith("ref_"):
            users[user_key]["traffic_source"] = ref_code
            sources = load_traffic_sources()
            if ref_code not in sources:
                sources[ref_code] = {
                    "total_visits": 0,
                    "total_registrations": 0,
                    "total_purchases": 0,
                    "total_revenue": 0.0,
                    "created_at": datetime.now().isoformat(),
                }
            sources[ref_code]["total_visits"] += 1
            sources[ref_code]["total_registrations"] += 1
            save_traffic_sources(sources)
        
        own_code = hashlib.md5(f"{user_id}_ref_salt".encode()).hexdigest()[:8].upper()
        users[user_key]["referral_code"] = own_code
        
        if user_key not in referrals:
            referrals[user_key] = {
                "user_id": user_id,
                "referral_code": own_code,
                "referrals_list": [],
                "total_earned": 0.0,
            }
        else:
            referrals[user_key].setdefault("referral_code", own_code)
            referrals[user_key].setdefault("referrals_list", [])
            referrals[user_key].setdefault("total_earned", 0.0)
        
        save_referrals(referrals)
        save_users(users)
        return True
    
    users[user_key]["last_active"] = datetime.now().isoformat()
    if username:
        users[user_key]["username"] = username
    if full_name:
        users[user_key]["full_name"] = full_name
    
    own_code = users[user_key].get("referral_code")
    if not own_code:
        own_code = hashlib.md5(f"{user_id}_ref_salt".encode()).hexdigest()[:8].upper()
        users[user_key]["referral_code"] = own_code
    
    if user_key not in referrals:
        referrals[user_key] = {
            "user_id": user_id,
            "referral_code": own_code,
            "referrals_list": [],
            "total_earned": 0.0,
        }
    else:
        referrals[user_key].setdefault("referral_code", own_code)
        referrals[user_key].setdefault("referrals_list", [])
        referrals[user_key].setdefault("total_earned", 0.0)
    
    save_referrals(referrals)
    save_users(users)
    return False

DEFAULT_REQUISITES = {
    "uah": f"💳 <b>Карта Моно:</b> <code>4874 0700 2513 7454</code>",
    "stars": f"⭐ <b>Отправьте звёзды в ЛС:</b> @MaskYoY",
    "nft": f"🖼 <b>NFT оплата в ЛС:</b> @MaskYoY",
}

if not os.path.exists(REQUISITES_FILE):
    save_requisites(DEFAULT_REQUISITES)

def get_requisites(method: str) -> str:
    req = load_requisites()
    return req.get(method, DEFAULT_REQUISITES.get(method, "Уточните у продавца"))

# ==================== КАТАЛОГ ====================
CATEGORIES = {
    "regular": {
        "name": f"{p_emoji('cart')} Обычные номера",
        "products": {
            "🇲🇲 Мьянма (+95)": {"uah": 30, "stars": 40, "nft": False, "emoji": "🇲🇲"},
            "🇺🇸 США (+1)": {"uah": 45, "stars": 65, "nft": False, "emoji": "🇺🇸"},
            "🇨🇴 Колумбия (+57)": {"uah": 45, "stars": 65, "nft": False, "emoji": "🇨🇴"},
            "🇧🇩 Бангладеш (+880)": {"uah": 45, "stars": 65, "nft": False, "emoji": "🇧🇩"},
            "🇫🇷 Франция (+33)": {"uah": 75, "stars": 100, "nft": False, "emoji": "🇫🇷"},
            "🇧🇷 Бразилия (+55)": {"uah": 75, "stars": 100, "nft": False, "emoji": "🇧🇷"},
            "🇺🇿 Узбекистан (+998)": {"uah": 75, "stars": 100, "nft": False, "emoji": "🇺🇿"},
            "🇹🇭 Таиланд (+66)": {"uah": 80, "stars": 100, "nft": False, "emoji": "🇹🇭"},
            "🇬🇧 Великобритания (+44)": {"uah": 120, "stars": 115, "nft": False, "emoji": "🇬🇧"},
            "🇺🇦 Украина (+380)": {"uah": 150, "stars": 150, "nft": False, "emoji": "🇺🇦"},
            "🇧🇾 Беларусь (+375)": {"uah": 150, "stars": 200, "nft": False, "emoji": "🇧🇾"},
            "🇰🇿 Казахстан (+7)": {"uah": 150, "stars": 200, "nft": False, "emoji": "🇰🇿"},
            "🇵🇱 Польша (+48)": {"uah": 150, "stars": 200, "nft": False, "emoji": "🇵🇱"},
            "🇷🇺 Россия (+7)": {"uah": 150, "stars": 200, "nft": False, "emoji": "🇷🇺"},
            "🇩🇪 Германия (+49)": {"uah": 150, "stars": 200, "nft": False, "emoji": "🇩🇪"},
        },
    },
    "premium": {
        "name": f"{p_emoji('star')} Premium номера",
        "products": {
            "🇺🇸 США (+1)": {"uah": 180, "stars": 250, "nft": False, "emoji": "🇺🇸"},
            "🇨🇦 Канада (+1)": {"uah": 180, "stars": 250, "nft": False, "emoji": "🇨🇦"},
            "🇺🇿 Узбекистан (+998)": {"uah": 350, "stars": 400, "nft": False, "emoji": "🇺🇿"},
            "🇺🇦 Украина (+380)": {"uah": 350, "stars": 400, "nft": False, "emoji": "🇺🇦"},
            "🇰🇿 Казахстан (+7)": {"uah": "от 130 до 450", "stars": 500, "nft": False, "emoji": "🇰🇿"},
            "🇩🇪 Германия (+49)": {"uah": 400, "stars": 500, "nft": False, "emoji": "🇩🇪"},
        },
    },
    "physical": {
        "name": f"{p_emoji('user')} Физические номера",
        "products": {
            "🇺🇸 США (+1)": {"uah": 100, "stars": 150, "nft": False, "emoji": "🇺🇸"},
            "🇺🇦 Украина (+380)": {"uah": 200, "stars": 300, "nft": False, "emoji": "🇺🇦"},
            "🇺🇿 Узбекистан (+998)": {"uah": 100, "stars": 150, "nft": False, "emoji": "🇺🇿"},
            "🇨🇴 Колумбия (+57)": {"uah": 100, "stars": 150, "nft": False, "emoji": "🇨🇴"},
            "🇹🇭 Таиланд (+66)": {"uah": 120, "stars": 175, "nft": False, "emoji": "🇹🇭"},
            "🇫🇷 Франция (+33)": {"uah": 150, "stars": 200, "nft": False, "emoji": "🇫🇷"},
            "🇰🇿 Казахстан (+77)": {"uah": 200, "stars": 300, "nft": False, "emoji": "🇰🇿"},
            "🇭🇺 Венгрия (+36)": {"uah": 200, "stars": 300, "nft": False, "emoji": "🇭🇺"},
            "🇬🇱 Гренландия (+299)": {"uah": 250, "stars": 350, "nft": False, "emoji": "🇬🇱"},
            "🇵🇱 Польша (+48)": {"uah": 250, "stars": 350, "nft": False, "emoji": "🇵🇱"},
        },
    },
}

# ==================== FSM ====================
class ReviewStates(StatesGroup):
    waiting_for_stars = State()
    waiting_for_photo_or_skip = State()
    waiting_for_text = State()

class OrderStates(StatesGroup):
    waiting_for_category = State()
    waiting_for_product = State()
    waiting_for_quantity = State()
    waiting_for_custom_quantity = State()
    waiting_for_payment_method = State()
    waiting_for_confirmation = State()

class CheckoutPromoStates(StatesGroup):
    waiting_for_promo_code = State()

class AdminStates(StatesGroup):
    waiting_for_order_id = State()
    waiting_for_phone = State()
    waiting_for_code = State()
    waiting_for_requisites_edit = State()
    waiting_for_broadcast = State()

class SupportStates(StatesGroup):
    chatting = State()

class PromoStates(StatesGroup):
    waiting_for_promo_code = State()

class AdminPromoStates(StatesGroup):
    waiting_for_promo_code = State()
    waiting_for_discount_type = State()
    waiting_for_discount_value = State()
    waiting_for_max_uses = State()
    waiting_for_expires_date = State()
    waiting_for_owner_id = State()
    waiting_for_commission_percent = State()

class AdminPromotionStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_products = State()
    waiting_for_new_prices = State()
    waiting_for_duration = State()

class AdminBroadcastTemplateStates(StatesGroup):
    waiting_for_days = State()
    waiting_for_text = State()
    waiting_for_button = State()

class AdminLevelStates(StatesGroup):
    waiting_for_level_choice = State()
    waiting_for_min_spent = State()
    waiting_for_discount = State()

class AdminReferralSettingsStates(StatesGroup):
    waiting_for_bonus_percent = State()

class AdminSearchStates(StatesGroup):
    waiting_for_query = State()

class AdminChatStates(StatesGroup):
    waiting_for_message = State()

STATUS_CONFIG = {
    "awaiting_payment": ("⏳", "Ожидает оплаты"),
    "paid": ("💳", "Оплачен"),
    "phone_sent": ("📱", "Номер отправлен"),
    "code_sent": ("🔑", "Код отправлен"),
    "completed": ("✅", "Выполнен"),
    "rejected": ("❌", "Отклонен"),
    "replaced": ("🔄", "Заменен"),
    "refunded": ("💰", "Возврат"),
}

def method_label(method: str) -> str:
    labels = {
        "uah": "💳 Гривны",
        "stars": "⭐ Stars",
        "nft": "🖼 NFT",
    }
    return labels.get(method, method)

def method_symbol(method: str) -> str:
    symbols = {
        "uah": "₴",
        "stars": "⭐",
        "nft": "💎",
    }
    return symbols.get(method, "")

def generate_order_id() -> str:
    return f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{os.urandom(2).hex().upper()}"

def generate_short_order_id() -> str:
    counter = load_order_counter()
    current = counter.get("current", 0)
    new_id = current + 1
    counter["current"] = new_id
    save_order_counter(counter)
    return f"#{new_id:06d}"

def get_user_level(user_id: int) -> dict:
    users = load_users()
    user = users.get(str(user_id), {})
    total_spent = user.get("total_spent", 0)
    
    levels = [
        ("VIP", get_setting("level_vip_min", 5000), get_setting("level_vip_discount", 10), "👑"),
        ("Платина", get_setting("level_platinum_min", 3000), get_setting("level_platinum_discount", 7), "💎"),
        ("Золото", get_setting("level_gold_min", 1500), get_setting("level_gold_discount", 5), "🥇"),
        ("Серебро", get_setting("level_silver_min", 500), get_setting("level_silver_discount", 3), "🥈"),
        ("Бронза", get_setting("level_bronze_min", 0), get_setting("level_bronze_discount", 0), "🥉"),
    ]
    
    for name, min_spent, discount, emoji in levels:
        if total_spent >= min_spent:
            return {
                "name": name,
                "discount": discount,
                "emoji": emoji,
                "min_spent": min_spent,
            }
    
    return {"name": "Бронза", "discount": 0, "emoji": "🥉", "min_spent": 0}

def find_order_key(orders: dict, order_id: str):
    if not order_id:
        return None
    order_id = str(order_id).strip()
    
    if order_id in orders:
        return order_id
    
    clean_id = order_id.replace("#", "").strip()
    
    for key, order in orders.items():
        if str(key).replace("#", "").strip() == clean_id:
            return key
        if str(order.get("order_id", "")).replace("#", "").strip() == clean_id:
            return key
        if str(order.get("short_id", "")).replace("#", "").strip() == clean_id:
            return key
    
    return None

async def process_referral_bonus(referrer_id: int, referred_id: int, order_total):
    try:
        order_total = float(order_total)
    except Exception:
        return
    
    if order_total <= 0:
        return
    
    referrals = load_referrals()
    referrer_key = str(referrer_id)
    
    if referrer_key not in referrals:
        return
    
    ref_data = referrals[referrer_key]
    if "referrals_list" not in ref_data:
        ref_data["referrals_list"] = []
    
    users = load_users()
    referred_user = users.get(str(referred_id), {})
    
    if referred_user.get("orders_count", 0) > 1:
        return
    
    for ref in ref_data["referrals_list"]:
        if ref.get("user_id") == referred_id and ref.get("bonus_promo_code"):
            return
    
    bonus_percent = get_setting("referral_bonus_percent", 5.0)
    bonus_amount = round(order_total * (bonus_percent / 100), 2)
    
    if bonus_amount <= 0:
        return
    
    code = "REF" + hashlib.md5(
        f"{referrer_id}_{referred_id}_{datetime.now().timestamp()}".encode()
    ).hexdigest()[:8].upper()
    
    promo_codes = load_promo_codes()
    promo_codes[code] = {
        "code": code,
        "discount_type": "fixed",
        "discount_value": bonus_amount,
        "max_uses": 1,
        "current_uses": 0,
        "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
        "is_active": True,
        "created_at": datetime.now().isoformat(),
        "description": f"Реферальный бонус за покупку пользователя {referred_id}",
        "owner_id": referrer_id,
        "commission_percent": 0,
    }
    save_promo_codes(promo_codes)
    
    for ref in ref_data["referrals_list"]:
        if ref.get("user_id") == referred_id:
            ref["first_purchase_done"] = True
            ref["bonus_amount"] = bonus_amount
            ref["bonus_promo_code"] = code
            break
    
    ref_data["total_earned"] = ref_data.get("total_earned", 0) + bonus_amount
    save_referrals(referrals)
    
    try:
        await bot.send_message(
            chat_id=referrer_id,
            text=(
                f"🎁 <b>Реферальный бонус!</b>\n\n"
                f"Ваш реферал совершил первую покупку.\n"
                f"Сумма бонуса: <b>{bonus_amount:.2f} ₴</b>\n"
                f"Ваш промокод: <code>{code}</code>\n\n"
                f"<i>Промокод одноразовый и действует 30 дней.</i>"
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Не удалось отправить реферальный бонус пользователю {referrer_id}: {e}")

def update_traffic_source_stats(source_name: str, purchases: int = 0, revenue=0.0):
    if not source_name:
        return
    try:
        revenue = float(revenue)
    except Exception:
        revenue = 0.0
    
    sources = load_traffic_sources()
    if source_name not in sources:
        sources[source_name] = {
            "total_visits": 0,
            "total_registrations": 0,
            "total_purchases": 0,
            "total_revenue": 0.0,
            "created_at": datetime.now().isoformat(),
        }
    
    sources[source_name]["total_purchases"] += purchases
    sources[source_name]["total_revenue"] += revenue
    save_traffic_sources(sources)

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=STORE_CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

async def schedule_reminder(order_id: str, delay_seconds: int = 300):
    await asyncio.sleep(delay_seconds)
    orders = load_orders()
    real_key = find_order_key(orders, order_id)
    
    if not real_key:
        return
    
    order = orders[real_key]
    
    if order["status"] == "completed" and not order.get("reviewed", False) and not order.get("reminder_sent", False):
        order["reminder_sent"] = True
        save_orders(orders)
        
        try:
            kb = InlineKeyboardBuilder()
            kb.button(text="⭐ Оставить отзыв", callback_data=f"leave_review_{real_key}")
            kb.button(text="📋 Мои заказы", callback_data="my_orders")
            kb.adjust(1)
            
            await bot.send_message(
                chat_id=order["user_id"],
                text=(
                    f"👋 <b>Напоминаем</b>\n\n"
                    f"Вы ещё не оставили отзыв о заказе <b>{order.get('short_id', real_key)}</b>.\n"
                    f"Нам очень важно ваше мнение!"
                ),
                reply_markup=kb.as_markup(),
            )
        except Exception as e:
            logger.error(f"Failed to send reminder for {real_key}: {e}")

# ==================== КЛАВИАТУРЫ ====================
def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🛍 Каталог"),
        KeyboardButton(text="🛒 Оформить заказ")
    )
    builder.row(
        KeyboardButton(text="📋 Мои заказы"),
        KeyboardButton(text="👤 Профиль")
    )
    builder.row(
        KeyboardButton(text="💬 Отзывы"),
        KeyboardButton(text="❓ FAQ")
    )
    builder.row(
        KeyboardButton(text="🎟 Промокод"),
        KeyboardButton(text="👥 Рефералы")
    )
    return builder.as_markup(resize_keyboard=True)

def get_admin_reply_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📊 Статистика"),
        KeyboardButton(text="📈 Панель управления")
    )
    builder.row(
        KeyboardButton(text="📋 Все заказы"),
        KeyboardButton(text="⏳ Ожидают оплаты")
    )
    builder.row(
        KeyboardButton(text="✅ Выполненные"),
        KeyboardButton(text="❌ Отклоненные")
    )
    builder.row(
        KeyboardButton(text="💰 Реквизиты"),
        KeyboardButton(text="📢 Рассылка")
    )
    builder.row(
        KeyboardButton(text="🔥 Акции"),
        KeyboardButton(text="🎟 Промокоды")
    )
    builder.row(
        KeyboardButton(text="⭐ Уровни"),
        KeyboardButton(text="👥 Рефералы")
    )
    builder.row(
        KeyboardButton(text="📊 Аналитика"),
        KeyboardButton(text="🔗 Источники")
    )
    return builder.as_markup(resize_keyboard=True)

def subscribe_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📢 Подписаться", url="http://t.me/owerpass_store")
    kb.button(text="✅ Я подписался", callback_data="check_sub")
    kb.adjust(1)
    return kb.as_markup()

def main_menu_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🛍 Каталог", callback_data="menu_catalog")
    kb.button(text="📋 Заказы", callback_data="my_orders")
    kb.button(text="💬 Отзывы", callback_data="menu_reviews")
    kb.button(text="❓ FAQ", callback_data="show_faq")
    kb.button(text="👤 Профиль", callback_data="profile_menu")
    kb.button(text="👥 Рефералы", callback_data="referral_menu")
    kb.button(text="🎟 Промокод", callback_data="promo_menu")
    kb.button(text="📢 Канал", url="http://t.me/owerpass_store")
    kb.adjust(2, 2, 2, 2)
    return kb.as_markup()

def catalog_keyboard():
    kb = InlineKeyboardBuilder()
    for cat_key, cat_data in CATEGORIES.items():
        kb.button(text=cat_data["name"], callback_data=f"cat_{cat_key}")
    kb.button(text="⬅️ Назад", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()

def category_products_keyboard(category: str):
    kb = InlineKeyboardBuilder()
    promotions = load_promotions()
    active_promos = {}
    now = datetime.now()
    
    for promo_id, promo in promotions.items():
        if promo.get("is_active", True):
            starts = promo.get("starts_at")
            ends = promo.get("ends_at")
            if starts and ends:
                start_dt = datetime.fromisoformat(starts)
                end_dt = datetime.fromisoformat(ends)
                if start_dt <= now <= end_dt:
                    active_promos.update(promo.get("new_prices", {}))
    
    for product_name, price_data in CATEGORIES[category]["products"].items():
        clean_name = product_name
        for emoji in ["🇲🇲", "🇺🇸", "🇨🇴", "🇧🇩", "🇫🇷", "🇧🇷", "🇺🇿", "🇹🇭",
                      "🇬🇧", "🇺🇦", "🇧🇾", "🇰🇿", "🇵🇱", "🇷🇺", "🇩🇪", "🇨🇦",
                      "🇭🇺", "🇬🇱"]:
            if product_name.startswith(emoji):
                clean_name = product_name[len(emoji):].strip()
                break
        
        nft_tag = " 🖼" if price_data.get("nft") else ""
        uah_price = price_data["uah"]
        
        if product_name in active_promos:
            promo_price = active_promos[product_name]
            if isinstance(uah_price, str):
                display = f"🔥 {product_name} — {promo_price}₴ <i>(было {uah_price})</i>{nft_tag}"
            else:
                display = f"🔥 {product_name} — {promo_price}₴ <i>(было {uah_price}₴)</i>{nft_tag}"
        else:
            if isinstance(uah_price, str):
                display = f"{product_name} — {uah_price}₴ / {price_data['stars']}⭐{nft_tag}"
            else:
                display = f"{product_name} — {uah_price}₴ / {price_data['stars']}⭐{nft_tag}"
        
        kb.button(text=display, callback_data=f"product_{category}_{clean_name}")
    
    kb.button(text="⬅️ В каталог", callback_data="menu_catalog")
    kb.adjust(1)
    return kb.as_markup()

def quantity_keyboard():
    kb = InlineKeyboardBuilder()
    for i in range(1, 6):
        kb.button(text=f"{i} шт.", callback_data=f"qty_{i}")
    kb.button(text="🔢 Другое", callback_data="qty_custom")
    kb.button(text="❌ Отмена", callback_data="main_menu", style="danger")
    kb.adjust(5, 1, 1)
    return kb.as_markup()

def payment_method_keyboard(can_nft: bool = False):
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Гривны", callback_data="pay_uah", style="primary")
    kb.button(text="⭐ Stars", callback_data="pay_stars", style="primary")
    if can_nft:
        kb.button(text="🖼 NFT", callback_data="pay_nft", style="primary")
    kb.button(text="❌ Отмена", callback_data="main_menu", style="danger")
    kb.adjust(2, 1)
    return kb.as_markup()

def confirm_order_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data="confirm_order", style="success")
    kb.button(text="🔢 Изменить кол-во", callback_data="edit_quantity")
    kb.button(text="💱 Способ оплаты", callback_data="edit_payment_method")
    kb.button(text="🎟 Промокод", callback_data="apply_promo_at_checkout")
    kb.button(text="❌ Отмена", callback_data="main_menu", style="danger")
    kb.adjust(1)
    return kb.as_markup()

def awaiting_payment_keyboard(order_id: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="💬 Написать продавцу", url="https://t.me/MaskYoY")
    kb.button(text="🆘 Поддержка в боте", callback_data=f"support_{order_id}")
    kb.button(text="📋 Мои заказы", callback_data="my_orders")
    kb.button(text="🏠 Меню", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()

def user_number_actions_keyboard(order_id: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="🔑 Запросить код", callback_data=f"user_request_code_{order_id}")
    kb.button(text="✅ Подтвердить вход", callback_data=f"user_confirm_login_{order_id}")
    kb.button(text="🆘 Поддержка", callback_data=f"support_{order_id}")
    kb.adjust(1)
    return kb.as_markup()

def user_order_actions_keyboard(order_id: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="⭐ Оставить отзыв", callback_data=f"leave_review_{order_id}")
    kb.button(text="🔄 Замена", callback_data=f"user_replace_{order_id}")
    kb.button(text="💰 Возврат", callback_data=f"user_refund_{order_id}")
    kb.button(text="🔁 Повторить", callback_data=f"repeat_order_{order_id}")
    kb.button(text="📋 Все заказы", callback_data="my_orders")
    kb.adjust(1)
    return kb.as_markup()

def reviews_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="👀 Смотреть отзывы", url="https://t.me/owerpass_repa")
    kb.button(text="⬅️ Назад", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()

def stars_keyboard():
    kb = InlineKeyboardBuilder()
    for i in range(1, 6):
        kb.button(text="⭐" * i, callback_data=f"stars_{i}")
    kb.adjust(5)
    return kb.as_markup()

def review_photo_skip_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="⏩ Пропустить", callback_data="skip_photo")
    kb.button(text="❌ Отмена", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()

def moderation_keyboard(review_id: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Одобрить", callback_data=f"approve_{review_id}", style="success")
    kb.button(text="❌ Отклонить", callback_data=f"reject_{review_id}", style="danger")
    kb.adjust(2)
    return kb.as_markup()

def admin_order_management_keyboard(order_id: str, status: str):
    kb = InlineKeyboardBuilder()
    if status == "awaiting_payment":
        kb.button(text="✅ Подтвердить оплату", callback_data=f"admin_confirm_payment_{order_id}", style="success")
        kb.button(text="❌ Отклонить", callback_data=f"admin_reject_{order_id}", style="danger")
    elif status == "paid":
        kb.button(text="📱 Выдать номер", callback_data=f"admin_send_phone_{order_id}")
        kb.button(text="❌ Отклонить", callback_data=f"admin_reject_{order_id}", style="danger")
    elif status == "phone_sent":
        kb.button(text="🔑 Выдать код", callback_data=f"admin_send_code_{order_id}")
        kb.button(text="❌ Отклонить", callback_data=f"admin_reject_{order_id}", style="danger")
    elif status == "code_sent":
        kb.button(text="✅ Завершить", callback_data=f"admin_confirm_login_{order_id}", style="success")
        kb.button(text="❌ Отклонить", callback_data=f"admin_reject_{order_id}", style="danger")
    elif status == "completed":
        kb.button(text="💰 Возврат", callback_data=f"admin_refund_{order_id}")
    kb.button(text="⬅️ Назад", callback_data="admin_back_to_list")
    kb.button(text="🔄 Обновить", callback_data=f"admin_order_detail_{order_id}")
    kb.adjust(1)
    return kb.as_markup()

def admin_all_orders_keyboard(page: int = 0, per_page: int = 5, status_filter: str = None):
    kb = InlineKeyboardBuilder()
    orders = load_orders()
    
    if status_filter:
        filtered = {k: v for k, v in orders.items() if v["status"] == status_filter}
    else:
        filtered = orders
    
    order_list = sorted(filtered.items(), reverse=True)
    total_pages = (len(order_list) + per_page - 1) // per_page
    
    if total_pages == 0:
        kb.button(text="🔄 Обновить", callback_data="admin_page_0")
        kb.adjust(1)
        return kb.as_markup()
    
    start = page * per_page
    end = start + per_page
    
    for order_id, order in order_list[start:end]:
        emoji, status_text = STATUS_CONFIG.get(order["status"], ("❓", "Неизвестно"))
        symbol = method_symbol(order.get("payment_method", "uah"))
        short_id = order.get("short_id", order_id[:8])
        
        if isinstance(order["total"], str):
            total_text = order["total"]
        else:
            total_text = f"{order['total']}{symbol}"
        
        kb.button(
            text=f"{emoji} {short_id} | {order['product'][:15]} | {total_text}",
            callback_data=f"admin_order_detail_{order_id}",
        )
    
    if total_pages > 1:
        if page > 0:
            kb.button(text="⬅️", callback_data=f"admin_page_{page - 1}")
        if page < total_pages - 1:
            kb.button(text="➡️", callback_data=f"admin_page_{page + 1}")
        kb.button(text="🔄 Обновить", callback_data=f"admin_page_{page}")
    
    if status_filter:
        kb.button(text="❌ Сбросить фильтр", callback_data="admin_page_0")
    
    kb.adjust(1)
    return kb.as_markup()

def requisites_edit_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Изменить гривны", callback_data="edit_req_uah")
    kb.button(text="⭐ Изменить звёзды", callback_data="edit_req_stars")
    kb.button(text="🖼 Изменить NFT", callback_data="edit_req_nft")
    kb.adjust(1)
    return kb.as_markup()

def profile_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="👥 Рефералы", callback_data="referral_menu")
    kb.button(text="📋 Заказы", callback_data="my_orders")
    kb.button(text="🔁 Последний заказ", callback_data="repeat_last_order")
    kb.button(text="⬅️ Главное меню", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()

def referral_menu_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Статистика", callback_data="referral_stats")
    kb.button(text="⬅️ Назад", callback_data="profile_menu")
    kb.adjust(1)
    return kb.as_markup()

def promo_menu_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()

def admin_dashboard_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📦 Заказы", callback_data="admin_orders_dashboard")
    kb.button(text="👥 Рефералы", callback_data="admin_referrals_dashboard")
    kb.button(text="🔥 Акции", callback_data="admin_promotions_dashboard")
    kb.button(text="🎟 Промокоды", callback_data="admin_promo_dashboard")
    kb.button(text="⭐ Уровни", callback_data="admin_levels_dashboard")
    kb.button(text="📢 Рассылки", callback_data="admin_broadcasts_dashboard")
    kb.button(text="📊 Аналитика", callback_data="admin_analytics_dashboard")
    kb.button(text="🔗 Источники", callback_data="admin_traffic_dashboard")
    kb.button(text="🔄 Обновить", callback_data="admin_dashboard_refresh")
    kb.adjust(2, 2, 2, 2, 1)
    return kb.as_markup()

def admin_promotions_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Создать акцию", callback_data="admin_create_promotion")
    
    promotions = load_promotions()
    for promo_id, promo in list(promotions.items())[:10]:
        status = "🟢" if promo.get("is_active", True) else "🔴"
        kb.button(
            text=f"{status} {promo.get('name', 'Без названия')}",
            callback_data=f"admin_promo_detail_{promo_id}",
        )
    
    kb.button(text="⬅️ Назад", callback_data="admin_dashboard_refresh")
    kb.adjust(1)
    return kb.as_markup()

def admin_promo_codes_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Создать промокод", callback_data="admin_create_promo_code")
    
    promo_codes = load_promo_codes()
    earnings = load_promo_earnings()
    
    for code, data in list(promo_codes.items())[:10]:
        status = "🟢" if data.get("is_active", True) else "🔴"
        uses = f"{data.get('current_uses', 0)}/{data.get('max_uses', '∞')}"
        earned = earnings.get(code, {}).get("total_earned", 0)
        kb.button(
            text=f"{status} {code} ({uses}) 💰{earned:.0f}₴",
            callback_data=f"admin_promo_code_detail_{code}",
        )
    
    kb.button(text="⬅️ Назад", callback_data="admin_dashboard_refresh")
    kb.adjust(1)
    return kb.as_markup()

def admin_levels_keyboard():
    kb = InlineKeyboardBuilder()
    levels = [
        ("bronze", "Бронза", "🥉"),
        ("silver", "Серебро", "🥈"),
        ("gold", "Золото", "🥇"),
        ("platinum", "Платина", "💎"),
        ("vip", "VIP", "👑"),
    ]
    for key, name, emoji in levels:
        kb.button(text=f"{emoji} {name}", callback_data=f"admin_edit_level_{key}")
    kb.button(text="⬅️ Назад", callback_data="admin_dashboard_refresh")
    kb.adjust(1)
    return kb.as_markup()

def admin_broadcasts_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Создать рассылку", callback_data="admin_create_broadcast_template")
    
    broadcasts = load_broadcasts()
    for bc_id, bc in broadcasts.items():
        status = "🟢" if bc.get("is_active", True) else "🔴"
        kb.button(
            text=f"{status} {bc.get('days_inactive', '?')} дней",
            callback_data=f"admin_broadcast_detail_{bc_id}",
        )
    
    kb.button(text="⬅️ Назад", callback_data="admin_dashboard_refresh")
    kb.adjust(1)
    return kb.as_markup()

def admin_referrals_settings_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Изменить бонус %", callback_data="admin_edit_referral_bonus")
    kb.button(text="⬅️ Назад", callback_data="admin_dashboard_refresh")
    kb.adjust(1)
    return kb.as_markup()

def admin_traffic_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="admin_dashboard_refresh")
    kb.adjust(1)
    return kb.as_markup()

def admin_analytics_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📈 По дням", callback_data="admin_analytics_by_days")
    kb.button(text="⏰ По часам", callback_data="admin_analytics_by_hours")
    kb.button(text="🌍 По странам", callback_data="admin_analytics_by_country")
    kb.button(text="⬅️ Назад", callback_data="admin_dashboard_refresh")
    kb.adjust(1)
    return kb.as_markup()

def admin_order_card_keyboard(order_id: str, status: str, user_id: int):
    kb = InlineKeyboardBuilder()
    if status == "awaiting_payment":
        kb.button(text="✅ Подтвердить", callback_data=f"admin_confirm_payment_{order_id}", style="success")
    elif status == "paid":
        kb.button(text="📱 Выдать номер", callback_data=f"admin_send_phone_{order_id}")
    elif status == "phone_sent":
        kb.button(text="🔑 Выдать код", callback_data=f"admin_send_code_{order_id}")
    elif status == "code_sent":
        kb.button(text="✅ Завершить", callback_data=f"admin_confirm_login_{order_id}", style="success")
    elif status == "completed":
        kb.button(text="💰 Возврат", callback_data=f"admin_refund_{order_id}")
    
    kb.button(text="💬 Чат с покупателем", callback_data=f"admin_chat_with_user_{order_id}")
    kb.button(text="❌ Отменить", callback_data=f"admin_reject_{order_id}", style="danger")
    kb.button(text="⬅️ Назад", callback_data="admin_back_to_list")
    kb.button(text="🔄 Обновить", callback_data=f"admin_order_detail_{order_id}")
    kb.adjust(1)
    return kb.as_markup()

# ==================== ТЕКСТЫ ====================
FAQ_TEXT = f"""
<b>{p_emoji('warn')} Частые вопросы</b>

<b>🛒 Как купить?</b>
1️⃣ Выберите товар в каталоге
2️⃣ Укажите количество
3️⃣ Выберите способ оплаты
4️⃣ Подтвердите заказ
5️⃣ Оплатите и свяжитесь с продавцом

<b>💳 Способы оплаты:</b>
• 💳 Гривны — перевод на карту
• ⭐ Telegram Stars
• 🖼 NFT

<b>🎁 Бонусы:</b>
• 5% с первой покупки реферала
• Скидки по уровням: Бронза → VIP

<b>📞 Контакты:</b>
• Продавец: @MaskYoY
• Канал: @owerpass_store
• Отзывы: @owerpass_repa
"""

# ==================== СТАРТ ====================
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    ref_code = None
    if message.text and len(message.text.split()) > 1:
        ref_code = message.text.split()[1]
    
    is_new = await add_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
        ref_code=ref_code,
    )
    
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            f"🔐 <b>Админ-панель</b>\n\nВыберите действие:",
            reply_markup=get_admin_reply_keyboard(),
        )
        return
    
    if not await check_subscription(message.from_user.id):
        await message.answer(
            "⚠️ <b>Подпишитесь на канал</b>\n\nДля доступа к магазину необходимо подписаться!",
            reply_markup=subscribe_keyboard(),
        )
        return
    
    welcome_text = f"{p_emoji('star')} <b>Добро пожаловать!</b>\n\n"
    welcome_text += "🔹 Продажа номеров Telegram\n"
    welcome_text += "🔹 Аккаунты TikTok, Discord\n"
    welcome_text += "🔹 Эксклюзивные юзернеймы\n\n"
    
    if is_new and ref_code:
        if ref_code.startswith("ref_"):
            welcome_text += "🎁 Вы зарегистрированы по реферальной ссылке!\n"
            welcome_text += "<i>Совершите первую покупку, чтобы ваш друг получил бонус!</i>\n\n"
        else:
            welcome_text += f"📊 Источник: <code>{ref_code}</code>\n\n"
    
    welcome_text += "Используйте кнопки ниже:"
    
    await message.answer(welcome_text, reply_markup=get_main_reply_keyboard())

# ==================== АДМИН: СТАТИСТИКА ====================
@dp.message(F.from_user.id == ADMIN_ID, F.text == "📊 Статистика")
async def admin_statistics(message: types.Message):
    orders = load_orders()
    users = load_users()
    
    total_orders = len(orders)
    status_counts = {}
    total_revenue_uah = 0
    total_revenue_stars = 0
    
    for order in orders.values():
        status = order["status"]
        status_counts[status] = status_counts.get(status, 0) + 1
        
        if order["status"] == "completed" and not isinstance(order.get("total", 0), str):
            if order.get("payment_method") == "uah":
                total_revenue_uah += order.get("total", 0)
            elif order.get("payment_method") == "stars":
                total_revenue_stars += order.get("total", 0)
    
    text = (
        f"📊 <b>Статистика магазина</b>\n\n"
        f"👤 Пользователей: <b>{len(users)}</b>\n"
        f"📦 Заказов: <b>{total_orders}</b>\n\n"
        f"✅ Выполнено: {status_counts.get('completed', 0)}\n"
        f"🔄 В обработке: {status_counts.get('paid', 0) + status_counts.get('phone_sent', 0) + status_counts.get('code_sent', 0)}\n"
        f"⏳ Ожидают оплаты: {status_counts.get('awaiting_payment', 0)}\n"
        f"❌ Отклонено: {status_counts.get('rejected', 0)}\n\n"
        f"💰 <b>Доход:</b>\n"
        f"• Гривны: <b>{total_revenue_uah:.2f} ₴</b>\n"
        f"• Stars: <b>{total_revenue_stars} ⭐</b>\n\n"
        f"📈 Средний чек: <b>{total_revenue_uah // max(status_counts.get('completed', 1), 1)} ₴</b>"
    )
    
    await message.answer(text, reply_markup=get_admin_reply_keyboard())

# ... (остальные хендлеры аналогично обновляются с новым дизайном)

# Для экономии места я покажу ключевые изменения

# ==================== СОЗДАНИЕ ЗАКАЗА С КОМИССИЕЙ ПРОМОКОДА ====================
async def create_order(source, state: FSMContext):
    data = await state.get_data()
    category = data["category"]
    product = data["product"]
    quantity = data["quantity"]
    method = data["payment_method"]
    
    price_data = CATEGORIES[category]["products"][product]
    
    if isinstance(price_data[method], str):
        total = price_data[method]
        discount_amount = 0
    else:
        total = price_data[method] * quantity
    
    user_level = get_user_level(source.from_user.id)
    discount_percent = user_level.get("discount", 0)
    discount_amount = total * (discount_percent / 100)
    total = total - discount_amount
    
    symbol = method_symbol(method)
    promo_code = data.get("promo_code")
    promo_owner_commission = 0
    promo_owner_id = None
    
    if promo_code and isinstance(total, (int, float)):
        promo_codes = load_promo_codes()
        promo = promo_codes.get(promo_code.upper())
        
        if promo and promo.get("is_active", True):
            expired = False
            if promo.get("expires_at"):
                expires = datetime.fromisoformat(promo["expires_at"])
                if datetime.now() > expires:
                    expired = True
            
            if promo.get("max_uses") and promo.get("current_uses", 0) >= promo["max_uses"]:
                expired = True
            
            if not expired:
                # Расчет скидки по промокоду
                if promo["discount_type"] == "percent":
                    promo_discount = total * (promo["discount_value"] / 100)
                else:
                    promo_discount = min(promo["discount_value"], total)
                
                # Расчет комиссии владельца промокода (20% от суммы заказа ДО скидки)
                original_total_before_promo = total + promo_discount
                commission_percent = promo.get("commission_percent", get_setting("promo_owner_commission_percent", 20.0))
                promo_owner_commission = original_total_before_promo * (commission_percent / 100)
                promo_owner_id = promo.get("owner_id")
                
                total = total - promo_discount
                discount_amount += promo_discount
                
                # Обновление использования промокода
                promo["current_uses"] = promo.get("current_uses", 0) + 1
                promo_codes[promo_code.upper()] = promo
                save_promo_codes(promo_codes)
                
                # Сохранение заработка владельца промокода
                if promo_owner_id:
                    earnings = load_promo_earnings()
                    if promo_code.upper() not in earnings:
                        earnings[promo_code.upper()] = {
                            "code": promo_code.upper(),
                            "owner_id": promo_owner_id,
                            "total_earned": 0,
                            "transactions": [],
                        }
                    
                    earnings[promo_code.upper()]["total_earned"] += promo_owner_commission
                    earnings[promo_code.upper()]["transactions"].append({
                        "order_id": None,  # будет заполнено позже
                        "amount": promo_owner_commission,
                        "date": datetime.now().isoformat(),
                        "buyer_id": source.from_user.id,
                    })
                    save_promo_earnings(earnings)
    
    legacy_order_id = generate_order_id()
    short_id = generate_short_order_id()
    
    if isinstance(source, types.CallbackQuery):
        username = source.from_user.username or "нет имени"
        user_id = source.from_user.id
        user_full_name = source.from_user.full_name
        target = source.message
    else:
        username = source.from_user.username or "нет имени"
        user_id = source.from_user.id
        user_full_name = source.from_user.full_name
        target = source
    
    category_name = CATEGORIES[category]["name"]
    
    orders = load_orders()
    orders[legacy_order_id] = {
        "order_id": legacy_order_id,
        "short_id": short_id,
        "user_id": user_id,
        "username": username,
        "full_name": user_full_name,
        "category": category,
        "category_name": category_name,
        "product": product,
        "quantity": quantity,
        "payment_method": method,
        "price_per_unit": price_data[method] if not isinstance(price_data[method], str) else price_data[method],
        "total": total,
        "discount_amount": discount_amount,
        "promo_code": promo_code,
        "promo_owner_commission": promo_owner_commission,
        "promo_owner_id": promo_owner_id,
        "status": "awaiting_payment",
        "created_at": datetime.now().isoformat(),
        "phone": None,
        "code": None,
        "reviewed": False,
        "reminder_sent": False,
    }
    save_orders(orders)
    
    # Обновление order_id в earnings
    if promo_owner_commission > 0:
        earnings = load_promo_earnings()
        if promo_code.upper() in earnings and earnings[promo_code.upper()]["transactions"]:
            earnings[promo_code.upper()]["transactions"][-1]["order_id"] = legacy_order_id
            save_promo_earnings(earnings)
    
    if isinstance(total, str):
        total_display = total
    else:
        total_display = f"{total:.2f} {symbol}"
    
    # Уведомление админу
    admin_msg = (
        f"📱 <b>Новый заказ {short_id}</b>\n\n"
        f"👤 @{username} | {user_full_name}\n"
        f"ID: <code>{user_id}</code>\n\n"
        f"📂 {category_name}\n"
        f"📦 {product}\n"
        f"🔢 {quantity} шт.\n"
        f"💳 {method_label(method)}\n"
        f"💰 <b>{total_display}</b>\n"
    )
    
    if discount_amount > 0:
        admin_msg += f"🎁 Скидки: -{discount_amount:.2f} {symbol}\n"
    
    if promo_code and promo_owner_commission > 0:
        admin_msg += f"\n🎟 Промокод: <code>{promo_code}</code>\n"
        admin_msg += f"💰 Комиссия владельцу: <b>{promo_owner_commission:.2f} ₴</b>\n"
        
        # Получаем имя владельца промокода
        if promo_owner_id:
            users = load_users()
            owner = users.get(str(promo_owner_id), {})
            owner_name = owner.get("username", f"ID:{promo_owner_id}")
            admin_msg += f"👤 Владелец: @{owner_name}\n"
    
    admin_msg += f"\nСтатус: ⏳ Ожидает оплаты"
    
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_msg,
            reply_markup=admin_order_management_keyboard(legacy_order_id, "awaiting_payment"),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Failed to send admin notification: {e}")
    
    # Сообщение пользователю
    requisites = get_requisites(method)
    payment_msg = (
        f"✅ <b>Заказ {short_id} создан!</b>\n\n"
        f"📂 {category_name}\n"
        f"📦 {product}\n"
        f"🔢 {quantity} шт.\n"
        f"💳 {method_label(method)}\n"
        f"💰 <b>{total_display}</b>\n"
    )
    
    if discount_amount > 0:
        payment_msg += f"🎁 Скидки: -{discount_amount:.2f} {symbol}\n"
    
    payment_msg += f"\n📌 <b>Реквизиты:</b>\n{requisites}\n\n"
    payment_msg += f"<i>После оплаты нажмите кнопку связи с продавцом.</i>"
    
    try:
        await target.edit_text(payment_msg, reply_markup=awaiting_payment_keyboard(legacy_order_id), parse_mode="HTML")
    except Exception:
        await target.answer(payment_msg, reply_markup=awaiting_payment_keyboard(legacy_order_id), parse_mode="HTML")
    
    await state.clear()

# ==================== АДМИН: ПРОМОКОДЫ С КОМИССИЕЙ ====================
@dp.callback_query(F.from_user.id == ADMIN_ID, F.data == "admin_create_promo_code")
async def admin_start_create_promo(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text("🎟 <b>Создание промокода</b>\n\nВведите код:")
    await state.set_state(AdminPromoStates.waiting_for_promo_code)

@dp.message(AdminPromoStates.waiting_for_promo_code, F.text)
async def admin_promo_code_input(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    await state.update_data(promo_code=code)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Процентная", callback_data="promo_type_percent")
    kb.button(text="💵 Фиксированная", callback_data="promo_type_fixed")
    kb.adjust(2)
    
    await message.answer(
        f"Код: <code>{code}</code>\n\nВыберите тип скидки:",
        reply_markup=kb.as_markup(),
        parse_mode="HTML",
    )
    await state.set_state(AdminPromoStates.waiting_for_discount_type)

@dp.callback_query(
    F.from_user.id == ADMIN_ID,
    AdminPromoStates.waiting_for_discount_type,
    F.data.startswith("promo_type_"),
)
async def admin_promo_type(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    discount_type = "percent" if callback.data == "promo_type_percent" else "fixed"
    await state.update_data(discount_type=discount_type)
    
    label = "процент (например, 10)" if discount_type == "percent" else "сумму в грн (например, 50)"
    await callback.message.edit_text(f"Введите {label}:")
    await state.set_state(AdminPromoStates.waiting_for_discount_value)

@dp.message(AdminPromoStates.waiting_for_discount_value, F.text)
async def admin_promo_discount_value(message: types.Message, state: FSMContext):
    try:
        value = float(message.text)
    except ValueError:
        await message.answer("❌ Введите корректное число")
        return
    
    await state.update_data(discount_value=value)
    await message.answer("Введите ID владельца промокода (кто будет получать комиссию):")
    await state.set_state(AdminPromoStates.waiting_for_owner_id)

@dp.message(AdminPromoStates.waiting_for_owner_id, F.text)
async def admin_promo_owner_id(message: types.Message, state: FSMContext):
    try:
        owner_id = int(message.text)
    except ValueError:
        await message.answer("❌ Введите корректный ID")
        return
    
    await state.update_data(owner_id=owner_id)
    
    current_commission = get_setting("promo_owner_commission_percent", 20.0)
    await message.answer(
        f"Введите процент комиссии для владельца (по умолчанию {current_commission}%):"
    )
    await state.set_state(AdminPromoStates.waiting_for_commission_percent)

@dp.message(AdminPromoStates.waiting_for_commission_percent, F.text)
async def admin_promo_commission_percent(message: types.Message, state: FSMContext):
    try:
        commission = float(message.text)
        if commission < 0 or commission > 100:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите число от 0 до 100")
        return
    
    await state.update_data(commission_percent=commission)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="♾ Без ограничений", callback_data="promo_unlimited")
    for n in [10, 50, 100, 500]:
        kb.button(text=f"{n} использований", callback_data=f"promo_max_{n}")
    kb.adjust(1)
    
    await message.answer("Максимальное количество использований:", reply_markup=kb.as_markup())
    await state.set_state(AdminPromoStates.waiting_for_max_uses)

@dp.callback_query(
    F.from_user.id == ADMIN_ID,
    AdminPromoStates.waiting_for_max_uses,
    F.data.startswith("promo_"),
)
async def admin_promo_max_uses(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    if callback.data == "promo_unlimited":
        max_uses = None
    else:
        max_uses = int(callback.data.split("_")[-1])
    
    await state.update_data(max_uses=max_uses)
    
    kb = InlineKeyboardBuilder()
    for days in [1, 7, 30, 90]:
        kb.button(text=f"{days} дней", callback_data=f"promo_expire_{days}")
    kb.button(text="♾ Навсегда", callback_data="promo_expire_0")
    kb.adjust(2)
    
    await callback.message.edit_text("Срок действия промокода:", reply_markup=kb.as_markup())
    await state.set_state(AdminPromoStates.waiting_for_expires_date)

@dp.callback_query(
    F.from_user.id == ADMIN_ID,
    AdminPromoStates.waiting_for_expires_date,
    F.data.startswith("promo_expire_"),
)
async def admin_promo_expires(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    days = int(callback.data.split("_")[-1])
    
    data = await state.get_data()
    expires_at = None
    if days > 0:
        expires_at = (datetime.now() + timedelta(days=days)).isoformat()
    
    promo_codes = load_promo_codes()
    promo_codes[data["promo_code"]] = {
        "code": data["promo_code"],
        "discount_type": data["discount_type"],
        "discount_value": data["discount_value"],
        "max_uses": data["max_uses"],
        "current_uses": 0,
        "expires_at": expires_at,
        "is_active": True,
        "created_at": datetime.now().isoformat(),
        "owner_id": data["owner_id"],
        "commission_percent": data["commission_percent"],
    }
    save_promo_codes(promo_codes)
    
    if data["discount_type"] == "percent":
        discount_desc = f"{data['discount_value']}%"
    else:
        discount_desc = f"{data['discount_value']} ₴"
    
    # Получаем имя владельца
    users = load_users()
    owner = users.get(str(data["owner_id"]), {})
    owner_name = owner.get("username", f"ID:{data['owner_id']}")
    
    text = (
        f"✅ <b>Промокод создан!</b>\n\n"
        f"🎟 Код: <code>{data['promo_code']}</code>\n"
        f"💰 Скидка: {discount_desc}\n"
        f"👤 Владелец: @{owner_name}\n"
        f"💵 Комиссия: {data['commission_percent']}%\n"
        f"🔢 Макс. использований: {data['max_uses'] or '♾'}\n"
    )
    
    if expires_at:
        text += f"📅 Действует до: {datetime.fromisoformat(expires_at).strftime('%d.%m.%Y')}\n"
    else:
        text += f"📅 Действует: навсегда\n"
    
    await callback.message.edit_text(text, reply_markup=admin_promo_codes_keyboard(), parse_mode="HTML")
    await state.clear()

@dp.callback_query(F.from_user.id == ADMIN_ID, F.data.startswith("admin_promo_code_detail_"))
async def admin_promo_code_detail(callback: types.CallbackQuery):
    await callback.answer()
    code = callback.data.replace("admin_promo_code_detail_", "")
    
    promo_codes = load_promo_codes()
    promo = promo_codes.get(code)
    
    if not promo:
        await callback.answer("❌ Промокод не найден", show_alert=True)
        return
    
    earnings = load_promo_earnings()
    earning_data = earnings.get(code, {})
    
    status = "🟢 Активен" if promo.get("is_active", True) else "🔴 Неактивен"
    
    if promo["discount_type"] == "percent":
        discount_desc = f"{promo['discount_value']}%"
    else:
        discount_desc = f"{promo['discount_value']} ₴"
    
    uses_text = f"{promo.get('current_uses', 0)}/{promo.get('max_uses') or '♾'}"
    total_earned = earning_data.get("total_earned", 0)
    
    # Получаем имя владельца
    users = load_users()
    owner_id = promo.get("owner_id")
    owner = users.get(str(owner_id), {}) if owner_id else {}
    owner_name = owner.get("username", f"ID:{owner_id}") if owner_id else "Не указан"
    
    text = (
        f"🎟 <b>Промокод {code}</b>\n\n"
        f"💰 Скидка: {discount_desc}\n"
        f"👤 Владелец: @{owner_name}\n"
        f"💵 Комиссия: {promo.get('commission_percent', 20)}%\n"
        f"<b>Статус:</b> {status}\n"
        f"🔢 Использований: {uses_text}\n"
        f"💰 Заработано: <b>{total_earned:.2f} ₴</b>\n"
    )
    
    if promo.get("expires_at"):
        text += f"📅 Действует до: {datetime.fromisoformat(promo['expires_at']).strftime('%d.%m.%Y')}\n"
    else:
        text += f"📅 Действует: навсегда\n"
    
    kb = InlineKeyboardBuilder()
    if promo.get("is_active", True):
        kb.button(text="🛑 Деактивировать", callback_data=f"admin_deactivate_promo_{code}")
    else:
        kb.button(text="✅ Активировать", callback_data=f"admin_activate_promo_{code}")
    kb.button(text="🗑 Удалить", callback_data=f"admin_delete_promo_{code}")
    kb.button(text="⬅️ Назад", callback_data="admin_promo_dashboard")
    kb.adjust(1)
    
    try:
        await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")

# ==================== ВЫДАЧА НОМЕРА (ИСПРАВЛЕННЫЙ ФОРМАТ) ====================
@dp.callback_query(F.from_user.id == ADMIN_ID, F.data.startswith("admin_send_phone_"))
async def admin_send_phone_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    order_id = callback.data.replace("admin_send_phone_", "")
    orders = load_orders()
    real_key = find_order_key(orders, order_id)
    if not real_key:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    order = orders[real_key]
    await state.update_data(admin_order_id=real_key)
    await callback.message.answer(
        f"📱 Отправьте номер телефона для заказа {order.get('short_id', real_key)}"
    )
    await state.set_state(AdminStates.waiting_for_phone)

@dp.message(AdminStates.waiting_for_phone)
async def admin_send_phone_process(message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("admin_order_id")
    if not order_id:
        await message.answer("❌ Ошибка: ID заказа не сохранён.")
        await state.clear()
        return
    
    phone_raw = message.text.strip()
    # Удаляем лишние символы, оставляем только цифры
    phone_digits = ''.join(filter(str.isdigit, phone_raw))
    
    orders = load_orders()
    real_key = find_order_key(orders, order_id)
    if not real_key:
        await message.answer("❌ Заказ не найден!")
        await state.clear()
        return
    
    order = orders[real_key]
    order_id = real_key
    short_id = order.get("short_id", order_id)
    
    # Сохраняем номер с плюсом
    phone_formatted = f"+{phone_digits}"
    
    order["phone"] = phone_formatted
    order["status"] = "phone_sent"
    order["phone_sent_at"] = datetime.now().isoformat()
    save_orders(orders)
    
    category_name = order.get("category_name", "Не указана")
    
    # Парсим страну из названия продукта
    product_name = order['product']
    country_name = "Неизвестно"
    country_code = ""
    
    # Простая логика извлечения страны из названия вида "🇺🇸 США (+1)"
    if "(" in product_name and ")" in product_name:
        parts = product_name.split("(")
        if len(parts) > 1:
            code_part = parts[1].replace(")", "").strip()
            country_code = code_part
        
        name_part = parts[0].strip()
        # Убираем флаг если есть
        for flag in ["🇲🇲", "🇺🇸", "🇨🇴", "🇧🇩", "🇫🇷", "🇧🇷", "🇺🇿", "🇹🇭", "🇬🇧", "🇺🇦", "🇧🇾", "🇰🇿", "🇵🇱", "🇷🇺", "🇩🇪", "🇨🇦", "🇭🇺", "🇬🇱"]:
            name_part = name_part.replace(flag, "").strip()
        country_name = name_part

    client_msg = (
        f"🎉 <b>ВАШ АККАУНТ</b>\n\n"
        f"🌍 Страна: {country_name} ({country_code})\n"
        f"📱 Ваш номер: {phone_formatted}\n\n"
        f"<b>Как войти:</b>\n"
        f"1. Войдите в новый аккаунт Telegram\n"
        f"2. Используйте номер указан выше для входа\n"
        f"3. Нажмите кнопку и получите код\n\n"
        f"<i>Код придёт сюда автоматически!</i>"
    )
    
    try:
        await bot.send_message(
            chat_id=order["user_id"],
            text=client_msg,
            reply_markup=user_number_actions_keyboard(order_id),
            parse_mode="HTML",
        )
        await message.answer(f"✅ Номер отправлен покупателю {short_id}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    
    await state.clear()

# ==================== ЗАПУСК ====================
async def main():
    print("=" * 50)
    print("OverPass Store Bot")
    print("Версия с премиум эмодзи и комиссией промокодов")
    print("=" * 50)
    
    await bot.delete_webhook(drop_pending_updates=True)
    await asyncio.sleep(1)
    
    print("Бот запущен!")
    print("=" * 50)
    
    asyncio.create_task(auto_broadcast_scheduler())
    
    try:
        await dp.start_polling(bot, drop_pending_updates=True)
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        await bot.session.close()
        print("Бот остановлен")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен пользователем")
    except Exception as e:
        print(f"Ошибка запуска: {e}")
        sys.exit(1)
