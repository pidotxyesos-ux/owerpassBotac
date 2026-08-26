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


# ==================== НАСТРОЙКИ ====================
DEFAULT_SETTINGS = {
    "referral_bonus_percent": 5.0,
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

        # Обработка реферального кода
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

        # Регистрация источника трафика, если это не реферальная ссылка
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

        # Сразу создаём личный реферальный код пользователя
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

    # Существующий пользователь
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
    "uah": "💳 Карта Моно: 4874 0700 2513 7454",
    "stars": "⭐ Отправьте звёзды в ЛС: @MaskYoY",
    "nft": "🖼 NFT оплата в ЛС: @MaskYoY",
}

if not os.path.exists(REQUISITES_FILE):
    save_requisites(DEFAULT_REQUISITES)


def get_requisites(method: str) -> str:
    req = load_requisites()
    return req.get(method, DEFAULT_REQUISITES.get(method, "Уточните у продавца"))


# ==================== КАТАЛОГ ====================
CATEGORIES = {
    "regular": {
        "name": "📞 ОБЫЧНЫЕ НОМЕРА",
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
        "name": "⭐️ НОМЕРА С TELEGRAM PREMIUM",
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
        "name": "☎️ ФИЗ НОМЕРА TELEGRAM",
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
        "uah": "Гривны (₴)",
        "stars": "Telegram Stars (⭐)",
        "nft": "NFT (TON)",
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
    """
    Ищет заказ по:
    - ключу в orders.json
    - order_id
    - короткому номеру #000001
    - номеру без #
    """
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
    """
    Реферальный бонус больше не зачисляется на баланс.
    Вместо этого реферер получает одноразовый промокод на сумму бонуса.
    """
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

    # Бонус даём только за первую покупку реферала
    if referred_user.get("orders_count", 0) > 1:
        return

    # Защита от повторного начисления
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
                f"🎁 Вы получили реферальный бонус!\n"
                f"Ваш реферал совершил первую покупку.\n"
                f"Сумма бонуса: {bonus_amount:.2f} грн\n\n"
                f"Ваш промокод: <code>{code}</code>\n"
                f"Промокод одноразовый и действует 30 дней."
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
                    f"👋 Напоминаем, что вы ещё не оставили отзыв о заказе {order.get('short_id', real_key)}.\n"
                    f"Нам очень важно ваше мнение! Поделитесь впечатлениями."
                ),
                reply_markup=kb.as_markup(),
            )
        except Exception as e:
            logger.error(f"Failed to send reminder for {real_key}: {e}")


# ==================== КЛАВИАТУРЫ ====================
def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🛍 Каталог"), KeyboardButton(text="💬 Отзывы"))
    builder.row(KeyboardButton(text="📋 Мои заказы"), KeyboardButton(text="❓ Частые вопросы"))
    builder.row(KeyboardButton(text="📢 Наш Канал"), KeyboardButton(text="🛒 Оформить заказ"))
    builder.row(KeyboardButton(text="👤 Профиль"), KeyboardButton(text="👥 Рефералы"))
    builder.row(KeyboardButton(text="🎟 Промокод"))
    return builder.as_markup(resize_keyboard=True)


def get_admin_reply_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📋 Все заказы"))
    builder.row(KeyboardButton(text="⏳ Ожидают оплаты"), KeyboardButton(text="🔄 В процессе"))
    builder.row(KeyboardButton(text="✅ Выполненные"), KeyboardButton(text="❌ Отклоненные"))
    builder.row(KeyboardButton(text="💰 Реквизиты"), KeyboardButton(text="📢 Рассылка"))
    builder.row(KeyboardButton(text="👤 Пользователи"), KeyboardButton(text="🏠 Главное меню"))
    builder.row(KeyboardButton(text="📈 Панель управления"), KeyboardButton(text="🔥 Акции"))
    builder.row(KeyboardButton(text="🎟 Промокоды"), KeyboardButton(text="⭐ Уровни"))
    builder.row(KeyboardButton(text="👥 Рефералы"), KeyboardButton(text="📢 Рассылки"))
    builder.row(KeyboardButton(text="📊 Аналитика"), KeyboardButton(text="🔗 Источники"))
    return builder.as_markup(resize_keyboard=True)


def subscribe_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📢 Подписаться на Магазин", url="http://t.me/owerpass_store")
    kb.button(text="✅ Я подписался", callback_data="check_sub")
    kb.adjust(1)
    return kb.as_markup()


def main_menu_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🛍 Каталог", callback_data="menu_catalog")
    kb.button(text="📋 Мои заказы", callback_data="my_orders")
    kb.button(text="💬 Отзывы", callback_data="menu_reviews")
    kb.button(text="❓ Частые вопросы", callback_data="show_faq")
    kb.button(text="👤 Профиль", callback_data="profile_menu")
    kb.button(text="👥 Рефералы", callback_data="referral_menu")
    kb.button(text="🎟 Промокод", callback_data="promo_menu")
    kb.button(text="📢 Наш Канал", url="http://t.me/owerpass_store")
    kb.adjust(2, 2, 2, 1)
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

        for emoji in [
            "🇲🇲", "🇺🇸", "🇨🇴", "🇧🇩", "🇫🇷", "🇧🇷", "🇺🇿", "🇹🇭",
            "🇬🇧", "🇺🇦", "🇧🇾", "🇰🇿", "🇵🇱", "🇷🇺", "🇩🇪", "🇨🇦",
            "🇭🇺", "🇬🇱",
        ]:
            if product_name.startswith(emoji):
                clean_name = product_name[len(emoji):].strip()
                break

        nft_tag = " 🖼" if price_data.get("nft") else ""
        uah_price = price_data["uah"]

        if product_name in active_promos:
            promo_price = active_promos[product_name]

            if isinstance(uah_price, str):
                display = f"🔥 {product_name} - {promo_price}₴ (было {uah_price}) {nft_tag}"
            else:
                display = f"🔥 {product_name} - {promo_price}₴ (было {uah_price}₴) {nft_tag}"
        else:
            if isinstance(uah_price, str):
                display = f"{product_name} - {uah_price}₴ / {price_data['stars']}⭐{nft_tag}"
            else:
                display = f"{product_name} - {uah_price}₴ / {price_data['stars']}⭐{nft_tag}"

        kb.button(text=display, callback_data=f"product_{category}_{clean_name}")

    kb.button(text="⬅️ В каталог", callback_data="menu_catalog")
    kb.adjust(1)
    return kb.as_markup()


def quantity_keyboard():
    kb = InlineKeyboardBuilder()
    for i in range(1, 6):
        kb.button(text=f"{i} шт.", callback_data=f"qty_{i}")
    kb.button(text="🔢 Другое количество", callback_data="qty_custom")
    kb.button(text="❌ Отмена", callback_data="main_menu")
    kb.adjust(5, 1, 1)
    return kb.as_markup()


def payment_method_keyboard(can_nft: bool = False):
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Оплатить гривнами (₴)", callback_data="pay_uah")
    kb.button(text="⭐ Оплатить звёздами", callback_data="pay_stars")

    if can_nft:
        kb.button(text="🖼 Оплатить NFT", callback_data="pay_nft")

    kb.button(text="❌ Отмена", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()


def confirm_order_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить заказ", callback_data="confirm_order")
    kb.button(text="🔢 Изменить количество", callback_data="edit_quantity")
    kb.button(text="💱 Изменить способ оплаты", callback_data="edit_payment_method")
    kb.button(text="🎟 Применить промокод", callback_data="apply_promo_at_checkout")
    kb.button(text="❌ Отмена", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()


def awaiting_payment_keyboard(order_id: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="💬 Написать продавцу в ЛС", url="https://t.me/MaskYoY")
    kb.button(text="🆘 Написать в боте", callback_data=f"support_{order_id}")
    kb.button(text="📋 Мои заказы", callback_data="my_orders")
    kb.button(text="🏠 Главное меню", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()


def user_number_actions_keyboard(order_id: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="🔑 Запросить код", callback_data=f"user_request_code_{order_id}")
    kb.button(text="✅ Подтвердить вход", callback_data=f"user_confirm_login_{order_id}")
    kb.button(text="🆘 Написать в боте", callback_data=f"support_{order_id}")
    kb.adjust(1)
    return kb.as_markup()


def user_order_actions_keyboard(order_id: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="⭐ Оставить отзыв", callback_data=f"leave_review_{order_id}")
    kb.button(text="🔄 Запросить замену", callback_data=f"user_replace_{order_id}")
    kb.button(text="💰 Запросить возврат", callback_data=f"user_refund_{order_id}")
    kb.button(text="🔁 Повторить заказ", callback_data=f"repeat_order_{order_id}")
    kb.button(text="📋 Все заказы", callback_data="my_orders")
    kb.adjust(1)
    return kb.as_markup()


def reviews_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="👀 Посмотреть отзывы", url="https://t.me/owerpass_repa")
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
    kb.button(text="⏩ Пропустить фото", callback_data="skip_photo")
    kb.button(text="❌ Отмена", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()


def moderation_keyboard(review_id: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Одобрить", callback_data=f"approve_{review_id}")
    kb.button(text="❌ Отклонить", callback_data=f"reject_{review_id}")
    kb.adjust(2)
    return kb.as_markup()


def admin_order_management_keyboard(order_id: str, status: str):
    kb = InlineKeyboardBuilder()

    if status == "awaiting_payment":
        kb.button(text="✅ Подтвердить оплату", callback_data=f"admin_confirm_payment_{order_id}")
        kb.button(text="❌ Отклонить", callback_data=f"admin_reject_{order_id}")
    elif status == "paid":
        kb.button(text="📱 Отправить номер", callback_data=f"admin_send_phone_{order_id}")
        kb.button(text="❌ Отклонить", callback_data=f"admin_reject_{order_id}")
    elif status == "phone_sent":
        kb.button(text="🔑 Отправить код", callback_data=f"admin_send_code_{order_id}")
        kb.button(text="❌ Отклонить", callback_data=f"admin_reject_{order_id}")
    elif status == "code_sent":
        kb.button(text="✅ Подтвердить вход", callback_data=f"admin_confirm_login_{order_id}")
        kb.button(text="❌ Отклонить", callback_data=f"admin_reject_{order_id}")
    elif status == "completed":
        kb.button(text="💰 Возврат", callback_data=f"admin_refund_{order_id}")
        kb.button(text="⬅️ Назад к списку", callback_data="admin_back_to_list")

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
    kb.button(text="📋 Мои заказы", callback_data="my_orders")
    kb.button(text="🔁 Повторить последний заказ", callback_data="repeat_last_order")
    kb.button(text="⬅️ Главное меню", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()


def referral_menu_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Моя статистика", callback_data="referral_stats")
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
    kb.button(text="🔗 Источники трафика", callback_data="admin_traffic_dashboard")
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

    for code, data in list(promo_codes.items())[:10]:
        status = "🟢" if data.get("is_active", True) else "🔴"
        uses = f"{data.get('current_uses', 0)}/{data.get('max_uses', '∞')}"
        kb.button(
            text=f"{status} {code} ({uses})",
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
        kb.button(text="✅ Подтвердить оплату", callback_data=f"admin_confirm_payment_{order_id}")
    elif status == "paid":
        kb.button(text="📱 Выдать номер", callback_data=f"admin_send_phone_{order_id}")
    elif status == "phone_sent":
        kb.button(text="🔑 Выдать код", callback_data=f"admin_send_code_{order_id}")
    elif status == "code_sent":
        kb.button(text="✅ Завершить", callback_data=f"admin_confirm_login_{order_id}")
    elif status == "completed":
        kb.button(text="💰 Возврат", callback_data=f"admin_refund_{order_id}")

    kb.button(text="💬 Написать покупателю", callback_data=f"admin_chat_with_user_{order_id}")
    kb.button(text="❌ Отменить", callback_data=f"admin_reject_{order_id}")
    kb.button(text="⬅️ Назад к списку", callback_data="admin_back_to_list")
    kb.button(text="🔄 Обновить", callback_data=f"admin_order_detail_{order_id}")
    kb.adjust(1)
    return kb.as_markup()


# ==================== ТЕКСТЫ ====================
FAQ_TEXT = """
❓ КАК КУПИТЬ НОМЕР?

1️⃣ Оформление заказа:
• Выберите категорию, товар и количество
• Выберите способ оплаты
• Подтвердите заказ

2️⃣ Оплата:
• После подтверждения вы получите реквизиты
• Оплатите и нажмите кнопку связи с продавцом
• Продавец подтвердит оплату

3️⃣ Получение номера:
• После подтверждения оплаты вам придет номер
• Нажмите «Запросить код» когда готовы войти
• Введите код и нажмите «Подтвердить вход»

4️⃣ Отзыв:
• После успешного входа оставьте отзыв

💳 Способы оплаты:
• Гривны (₴) — перевод на карту
• Telegram Stars (⭐)
• NFT

🎁 Бонусы:
• 5% с первой покупки реферала выдаётся промокодом
• Скидки по уровням: Бронза → VIP

📞 Контакты:
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
            "🔐 Админ-панель OverPass Store\nВыберите действие:",
            reply_markup=get_admin_reply_keyboard(),
        )
        return

    if not await check_subscription(message.from_user.id):
        await message.answer(
            "⚠️ Подпишитесь на канал магазина для доступа!",
            reply_markup=subscribe_keyboard(),
        )
        return

    welcome_text = "👋 Добро пожаловать в OverPass Store!\n"
    welcome_text += "🔹 Продажа номеров Telegram\n"
    welcome_text += "🔹 Аккаунты TikTok, Discord\n"
    welcome_text += "🔹 Эксклюзивные юзернеймы\n"

    if is_new and ref_code:
        if ref_code.startswith("ref_"):
            welcome_text += "🎁 Вы зарегистрированы по реферальной ссылке!\n"
            welcome_text += "Совершите первую покупку, чтобы ваш друг получил бонус!\n"
        else:
            welcome_text += f"📊 Источник: {ref_code}\n"

    welcome_text += "Выберите раздел в меню:"

    await message.answer(welcome_text, reply_markup=get_main_reply_keyboard())


# ==================== АДМИН: СТАТИСТИКА И ЗАКАЗЫ ====================
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
        f"📊 СТАТИСТИКА OverPass Store\n"
        f"👤 Всего пользователей: {len(users)}\n"
        f"📦 Всего заказов: {total_orders}\n"
        f"✅ Выполнено: {status_counts.get('completed', 0)}\n"
        f"🔄 В обработке: {status_counts.get('paid', 0) + status_counts.get('phone_sent', 0) + status_counts.get('code_sent', 0)}\n"
        f"⏳ Ожидают оплаты: {status_counts.get('awaiting_payment', 0)}\n"
        f"❌ Отклонено: {status_counts.get('rejected', 0)}\n"
        f"💰 ДОХОД (выполненные заказы):\n"
        f"• Гривны: {total_revenue_uah} ₴\n"
        f"• Звёзды: {total_revenue_stars} ⭐\n"
        f"📈 Средний чек: {total_revenue_uah // max(status_counts.get('completed', 1), 1)} ₴"
    )

    await message.answer(text, reply_markup=get_admin_reply_keyboard())


@dp.message(F.from_user.id == ADMIN_ID, F.text == "📋 Все заказы")
async def admin_all_orders(message: types.Message):
    await show_admin_orders_page(message, 0, status_filter=None)


@dp.message(F.from_user.id == ADMIN_ID, F.text == "⏳ Ожидают оплаты")
async def admin_pending_orders(message: types.Message):
    await show_admin_orders_page(message, 0, status_filter="awaiting_payment")


@dp.message(F.from_user.id == ADMIN_ID, F.text == "🔄 В процессе")
async def admin_in_progress_orders(message: types.Message):
    await show_admin_orders_page(message, 0, status_filter="paid")


@dp.message(F.from_user.id == ADMIN_ID, F.text == "✅ Выполненные")
async def admin_completed_orders(message: types.Message):
    await show_admin_orders_page(message, 0, status_filter="completed")


@dp.message(F.from_user.id == ADMIN_ID, F.text == "❌ Отклоненные")
async def admin_rejected_orders(message: types.Message):
    await show_admin_orders_page(message, 0, status_filter="rejected")


@dp.message(F.from_user.id == ADMIN_ID, F.text == "👤 Пользователи")
async def admin_users_list(message: types.Message):
    users = load_users()

    if not users:
        await message.answer("📋 Нет пользователей", reply_markup=get_admin_reply_keyboard())
        return

    text = f"👤 ВСЕГО ПОЛЬЗОВАТЕЛЕЙ: {len(users)}\n"
    users_list = sorted(users.items(), key=lambda x: x[1].get("first_seen", ""), reverse=True)[:10]

    for user_id, user_data in users_list:
        username = user_data.get("username", "нет имени")
        full_name = user_data.get("full_name", "Без имени")
        first_seen = user_data.get("first_seen", "")

        if first_seen:
            first_seen = datetime.fromisoformat(first_seen).strftime("%d.%m.%Y")

        text += f"👤 {full_name} (@{username})\nID: {user_id}\n📅 {first_seen}\n"

    if len(users) > 10:
        text += f"... и еще {len(users) - 10} пользователей"

    await message.answer(text, reply_markup=get_admin_reply_keyboard())


@dp.message(F.from_user.id == ADMIN_ID, F.text == "🏠 Главное меню")
async def admin_to_main_menu(message: types.Message):
    await message.answer(
        "🏠 Возврат в админ-меню",
        reply_markup=get_admin_reply_keyboard(),
    )


@dp.callback_query(F.data.startswith("admin_page_"))
async def admin_page_navigation(callback: types.CallbackQuery):
    await callback.answer()

    parts = callback.data.split("_")
    page = int(parts[2])
    status_filter = None

    await show_admin_orders_page(callback.message, page, status_filter=status_filter, edit=True)


async def show_admin_orders_page(target, page: int, status_filter: str = None, edit: bool = False):
    orders = load_orders()

    if status_filter:
        filtered = {k: v for k, v in orders.items() if v["status"] == status_filter}
    else:
        filtered = orders

    order_list = sorted(filtered.items(), reverse=True)
    per_page = 5

    if not order_list:
        text = "📋 Нет заказов"

        if edit:
            await target.edit_text(text, reply_markup=admin_all_orders_keyboard(0, per_page, status_filter))
        else:
            await target.answer(text, reply_markup=get_admin_reply_keyboard())

        return

    total_pages = (len(order_list) + per_page - 1) // per_page

    if page >= total_pages:
        page = total_pages - 1

    if page < 0:
        page = 0

    status_label = f" (фильтр: {STATUS_CONFIG.get(status_filter, ('', ''))[1]})" if status_filter else ""
    text = f"📋 ВСЕ ЗАКАЗЫ{status_label} (стр. {page + 1}/{total_pages})\n"

    start = page * per_page
    end = min(start + per_page, len(order_list))

    for order_id, order in order_list[start:end]:
        emoji, status_text = STATUS_CONFIG.get(order["status"], ("❓", "Неизвестно"))
        symbol = method_symbol(order.get("payment_method", "uah"))
        created = datetime.fromisoformat(order["created_at"]).strftime("%d.%m %H:%M")
        short_id = order.get("short_id", order_id[:8])

        text += (
            f"{emoji} {short_id} | {order['product'][:20]}\n"
            f"   👤 @{order['username']} | {order['total']} {symbol} | {status_text} | {created}\n"
        )

    if edit:
        await target.edit_text(text, reply_markup=admin_all_orders_keyboard(page, per_page, status_filter))
    else:
        await target.answer(text, reply_markup=admin_all_orders_keyboard(page, per_page, status_filter))


@dp.callback_query(F.data.startswith("admin_order_detail_"))
async def admin_order_detail(callback: types.CallbackQuery):
    await callback.answer()

    order_id = callback.data.replace("admin_order_detail_", "")

    orders = load_orders()
    real_key = find_order_key(orders, order_id)

    if not real_key:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    order = orders[real_key]
    order_id = real_key

    emoji, status_text = STATUS_CONFIG.get(order["status"], ("❓", "Неизвестно"))
    symbol = method_symbol(order.get("payment_method", "uah"))
    category_name = order.get("category_name", "Не указана")
    short_id = order.get("short_id", order_id[:8])

    timer_text = ""

    if order.get("paid_at"):
        paid_at = datetime.fromisoformat(order["paid_at"])
        elapsed = datetime.now() - paid_at
        minutes = int(elapsed.total_seconds() / 60)
        hours = minutes // 60

        if hours > 0:
            timer_text = f"\n⏱ Прошло после оплаты: {hours}ч {minutes % 60}мин"
        else:
            timer_text = f"\n⏱ Прошло после оплаты: {minutes} мин"

    elif order["status"] == "awaiting_payment" and order.get("created_at"):
        created = datetime.fromisoformat(order["created_at"])
        elapsed = datetime.now() - created
        minutes = int(elapsed.total_seconds() / 60)
        timer_text = f"\n⏱ Ожидает оплату: {minutes} мин"

    if isinstance(order["total"], str):
        total_text = order["total"]
    else:
        total_text = f"{order['total']} {symbol}"

    text = (
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📦 <b>Заказ {short_id}</b>\n"
        f"👤 <b>Покупатель</b>\n@{order.get('username', 'Нет')}\n"
        f"🆔 <b>ID</b>\n<code>{order['user_id']}</code>\n"
        f"📅 <b>Создано</b>\n{datetime.fromisoformat(order['created_at']).strftime('%d.%m.%Y %H:%M')}\n"
        f"🌍 <b>Товар</b>\n{order['product']}\n"
        f"📂 <b>Категория</b>\n{category_name}\n"
        f"📦 <b>Количество</b>\n{order['quantity']}\n"
        f"💳 <b>Оплата</b>\n{method_label(order['payment_method'])}\n"
        f"💰 <b>Сумма</b>\n{total_text}\n"
    )

    if order.get("phone"):
        text += f"📱 <b>Номер</b>\n{order['phone']}\n"
    else:
        text += f"📱 <b>Номер</b>\nне выдан\n"

    if order.get("code"):
        text += f"🔑 <b>Код</b>\n{order['code']}\n"
    else:
        text += f"🔑 <b>Код</b>\nне получен\n"

    text += f"<b>Статус</b>\n{emoji} {status_text}{timer_text}\n"

    chat_history = load_chat_history()

    if order_id in chat_history and chat_history[order_id]:
        text += "💬 <b>Чат:</b>\n"

        for msg in chat_history[order_id][-5:]:
            sender = "Покупатель" if msg["sender"] == "user" else "Админ"
            text += f"{sender}: {msg['text'][:50]}...\n"

        text += "\n"

    text += "━━━━━━━━━━━━━━━━━━"

    try:
        await callback.message.edit_text(
            text,
            reply_markup=admin_order_card_keyboard(order_id, order["status"], order["user_id"]),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=admin_order_card_keyboard(order_id, order["status"], order["user_id"]),
            parse_mode="HTML",
        )


@dp.callback_query(F.data == "admin_back_to_list")
async def admin_back_to_list(callback: types.CallbackQuery):
    await callback.answer()
    await show_admin_orders_page(callback.message, 0, status_filter=None, edit=True)


@dp.message(F.from_user.id == ADMIN_ID, F.text == "💰 Реквизиты")
async def admin_requisites(message: types.Message):
    req = load_requisites()

    text = (
        f"💰 ТЕКУЩИЕ РЕКВИЗИТЫ:\n"
        f"💳 Гривны:\n{req.get('uah', 'Не задано')}\n"
        f"⭐ Звёзды:\n{req.get('stars', 'Не задано')}\n"
        f"🖼 NFT:\n{req.get('nft', 'Не задано')}\n"
        f"Выберите что изменить:"
    )

    await message.answer(text, reply_markup=requisites_edit_keyboard())


@dp.callback_query(F.data.startswith("edit_req_"))
async def edit_requisite_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    method = callback.data.replace("edit_req_", "")
    labels = {"uah": "Гривны (₴)", "stars": "Звёзды", "nft": "NFT"}

    await state.update_data(edit_req_method=method)

    await callback.message.answer(
        f"✏️ Введите новые реквизиты для {labels.get(method, method)}:\n"
        f"Текущие:\n{get_requisites(method)}"
    )

    await state.set_state(AdminStates.waiting_for_requisites_edit)


@dp.message(AdminStates.waiting_for_requisites_edit)
async def save_requisite(message: types.Message, state: FSMContext):
    data = await state.get_data()
    method = data["edit_req_method"]

    req = load_requisites()
    req[method] = message.text
    save_requisites(req)

    labels = {"uah": "Гривны", "stars": "Звёзды", "nft": "NFT"}

    await message.answer(
        f"✅ Реквизиты для {labels.get(method, method)} обновлены!",
        reply_markup=get_admin_reply_keyboard(),
    )

    await state.clear()


# ==================== АДМИН: РАССЫЛКА ====================
@dp.message(F.from_user.id == ADMIN_ID, F.text == "📢 Рассылка")
async def admin_broadcast(message: types.Message, state: FSMContext):
    users = load_users()

    if not users:
        await message.answer("❌ Нет пользователей для рассылки", reply_markup=get_admin_reply_keyboard())
        return

    await message.answer(
        f"📢 Отправьте сообщение для рассылки всем {len(users)} пользователям.\n"
        f"💡 Вы можете отправить:\n"
        f"• Текст\n"
        f"• Фото/видео с подписью\n"
        f"• Документ\n"
        f"Чтобы отменить рассылку, отправьте /cancel",
        reply_markup=get_admin_reply_keyboard(),
    )

    await state.set_state(AdminStates.waiting_for_broadcast)


@dp.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await message.answer("❌ Рассылка отменена", reply_markup=get_admin_reply_keyboard())
        await state.clear()
        return

    users = load_users()
    total_users = len(users)
    success = 0
    failed = 0

    status_msg = await message.answer(f"⏳ Начинаю рассылку {total_users} пользователям...")

    for user_id_str, user_data in users.items():
        user_id = int(user_id_str)

        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )
            success += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            failed += 1
            logger.error(f"Failed to send broadcast to {user_id}: {e}")

    await status_msg.edit_text(
        f"✅ РАССЫЛКА ЗАВЕРШЕНА!\n"
        f"📤 Отправлено: {success}\n"
        f"❌ Не доставлено: {failed}\n"
        f"👥 Всего: {total_users}",
        reply_markup=get_admin_reply_keyboard(),
    )

    await state.clear()


@dp.message(Command("cancel"))
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state is None:
        return

    await state.clear()

    if message.from_user.id == ADMIN_ID:
        await message.answer("❌ Действие отменено", reply_markup=get_admin_reply_keyboard())
    else:
        await message.answer("❌ Действие отменено", reply_markup=get_main_reply_keyboard())


# ==================== АДМИН: УПРАВЛЕНИЕ ЗАКАЗАМИ ====================
@dp.callback_query(F.data.startswith("admin_confirm_payment_"))
async def admin_confirm_payment(callback: types.CallbackQuery):
    await callback.answer()

    order_id = callback.data.replace("admin_confirm_payment_", "")

    orders = load_orders()
    real_key = find_order_key(orders, order_id)

    if not real_key:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    order = orders[real_key]
    order_id = real_key

    order["status"] = "paid"
    order["paid_at"] = datetime.now().isoformat()
    save_orders(orders)

    symbol = method_symbol(order.get("payment_method", "uah"))
    category_name = order.get("category_name", "Не указана")
    short_id = order.get("short_id", order_id)

    client_msg = (
        f"✅ ОПЛАТА ПОДТВЕРЖДЕНА!\n"
        f"Заказ: {short_id}\n"
        f"📂 Категория: {category_name}\n"
        f"📦 Товар: {order['product']}\n"
        f"💰 Оплачено: {order.get('total', 0)} {symbol}\n"
        f"Продавец скоро отправит вам номер телефона.\n"
        f"Ожидайте уведомление в этом чате."
    )

    try:
        await bot.send_message(chat_id=order["user_id"], text=client_msg, parse_mode=None)
    except Exception:
        pass

    try:
        base_text = callback.message.text or callback.message.caption or "Заказ"

        await callback.message.edit_text(
            base_text + f"\n✅ <b>ОПЛАЧЕНО</b>\nДата: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            reply_markup=admin_order_management_keyboard(order_id, "paid"),
            parse_mode="HTML",
        )
    except Exception:
        pass


@dp.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject_order(callback: types.CallbackQuery):
    await callback.answer()

    order_id = callback.data.replace("admin_reject_", "")

    orders = load_orders()
    real_key = find_order_key(orders, order_id)

    if not real_key:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    order = orders[real_key]
    order_id = real_key

    order["status"] = "rejected"
    save_orders(orders)

    short_id = order.get("short_id", order_id)

    try:
        await bot.send_message(
            chat_id=order["user_id"],
            text=f"❌ Заказ {short_id} отклонен\nПо вопросам: @MaskYoY",
            parse_mode=None,
        )
    except Exception:
        pass

    try:
        base_text = callback.message.text or callback.message.caption or "Заказ"

        await callback.message.edit_text(
            base_text + f"\n❌ <b>ОТКЛОНЕН</b>",
            reply_markup=admin_order_management_keyboard(order_id, "rejected"),
            parse_mode="HTML",
        )
    except Exception:
        pass


@dp.callback_query(F.data.startswith("admin_send_phone_"))
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
        await message.answer("❌ Ошибка: ID заказа не сохранён. Нажми кнопку ещё раз.")
        await state.clear()
        return

    phone = message.text.strip()

    orders = load_orders()
    real_key = find_order_key(orders, order_id)

    if not real_key:
        await message.answer(
            f"❌ Заказ не найден!\n"
            f"Искал ID: {order_id}\n"
            f"Попробуй открыть карточку заказа заново."
        )
        await state.clear()
        return

    order = orders[real_key]
    order_id = real_key
    short_id = order.get("short_id", order_id)

    order["phone"] = phone
    order["status"] = "phone_sent"
    order["phone_sent_at"] = datetime.now().isoformat()
    save_orders(orders)

    category_name = order.get("category_name", "Не указана")

    client_msg = (
        f"📱 НОМЕР ТЕЛЕФОНА!\n"
        f"Заказ: {short_id}\n"
        f"📂 Категория: {category_name}\n"
        f"📦 Товар: {order['product']}\n"
        f"📱 Номер: {phone}\n"
        f"Когда будете готовы войти - нажмите «Запросить код»\n"
        f"Код приходит быстро, будьте готовы ввести его сразу!"
    )

    try:
        await bot.send_message(
            chat_id=order["user_id"],
            text=client_msg,
            reply_markup=user_number_actions_keyboard(order_id),
            parse_mode=None,
        )

        await message.answer(f"✅ Номер отправлен покупателю {short_id}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

    await state.clear()


@dp.callback_query(F.data.startswith("admin_send_code_"))
async def admin_send_code_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    order_id = callback.data.replace("admin_send_code_", "")

    orders = load_orders()
    real_key = find_order_key(orders, order_id)

    if not real_key:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    order = orders[real_key]

    await state.update_data(admin_order_id=real_key)

    await callback.message.answer(
        f"🔑 Отправьте код для заказа {order.get('short_id', real_key)}"
    )

    await state.set_state(AdminStates.waiting_for_code)


@dp.message(AdminStates.waiting_for_code)
async def admin_send_code_process(message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("admin_order_id")

    if not order_id:
        await message.answer("❌ Ошибка: ID заказа не сохранён. Нажми кнопку ещё раз.")
        await state.clear()
        return

    code = message.text.strip()

    orders = load_orders()
    real_key = find_order_key(orders, order_id)

    if not real_key:
        await message.answer(
            f"❌ Заказ не найден!\n"
            f"Искал ID: {order_id}\n"
            f"Попробуй открыть карточку заказа заново."
        )
        await state.clear()
        return

    order = orders[real_key]
    order_id = real_key
    short_id = order.get("short_id", order_id)

    order["code"] = code
    order["status"] = "code_sent"
    order["code_sent_at"] = datetime.now().isoformat()
    save_orders(orders)

    category_name = order.get("category_name", "Не указана")

    client_msg = (
        f"🔑 КОД ПОДТВЕРЖДЕНИЯ!\n"
        f"Заказ: {short_id}\n"
        f"📂 Категория: {category_name}\n"
        f"📦 Товар: {order['product']}\n"
        f"🔑 Код: {code}\n"
        f"Введите код в Telegram сейчас же!\n"
        f"После успешного входа нажмите «Подтвердить вход»"
    )

    try:
        await bot.send_message(
            chat_id=order["user_id"],
            text=client_msg,
            reply_markup=user_number_actions_keyboard(order_id),
            parse_mode=None,
        )

        await message.answer(f"✅ Код отправлен покупателю {short_id}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

    await state.clear()


@dp.callback_query(F.data.startswith("admin_confirm_login_"))
async def admin_confirm_login(callback: types.CallbackQuery):
    await callback.answer()

    order_id = callback.data.replace("admin_confirm_login_", "")

    orders = load_orders()
    real_key = find_order_key(orders, order_id)

    if not real_key:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    order = orders[real_key]
    order_id = real_key

    if order.get("status") == "completed":
        await callback.answer("✅ Заказ уже выполнен", show_alert=True)
        return

    order["status"] = "completed"
    order["completed_at"] = datetime.now().isoformat()
    order["reminder_sent"] = False
    save_orders(orders)

    users = load_users()
    user_key = str(order["user_id"])

    if user_key in users:
        users[user_key]["total_spent"] = users[user_key].get("total_spent", 0) + (
            order.get("total", 0) if not isinstance(order.get("total", 0), str) else 0
        )
        users[user_key]["orders_count"] = users[user_key].get("orders_count", 0) + 1

    save_users(users)

    if users[user_key].get("referred_by"):
        await process_referral_bonus(
            users[user_key]["referred_by"],
            order["user_id"],
            order.get("total", 0),
        )

    traffic_source = users[user_key].get("traffic_source")

    if traffic_source:
        update_traffic_source_stats(
            traffic_source,
            purchases=1,
            revenue=order.get("total", 0),
        )

    short_id = order.get("short_id", order_id)

    client_msg = (
        f"🎉 ЗАКАЗ ВЫПОЛНЕН!\n"
        f"Заказ: {short_id}\n"
        f"Товар: {order['product']}\n"
        f"Номер: {order.get('phone', 'Н/Д')}\n"
        f"Пожалуйста, оставьте отзыв о покупке!\n"
        f"Спасибо за покупку!"
    )

    try:
        await bot.send_message(
            chat_id=order["user_id"],
            text=client_msg,
            reply_markup=user_order_actions_keyboard(order_id),
            parse_mode=None,
        )
    except Exception:
        pass

    asyncio.create_task(schedule_reminder(order_id))

    try:
        base_text = callback.message.text or callback.message.caption or "Заказ"

        await callback.message.edit_text(
            base_text + f"\n✅ <b>ВХОД ПОДТВЕРЖДЕН!</b>",
            reply_markup=admin_order_management_keyboard(order_id, "completed"),
            parse_mode="HTML",
        )
    except Exception:
        pass


@dp.callback_query(F.data.startswith("admin_refund_"))
async def admin_refund_order(callback: types.CallbackQuery):
    await callback.answer()

    order_id = callback.data.replace("admin_refund_", "")

    orders = load_orders()
    real_key = find_order_key(orders, order_id)

    if not real_key:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    order = orders[real_key]
    order_id = real_key

    order["status"] = "refunded"
    save_orders(orders)

    short_id = order.get("short_id", order_id)

    try:
        await bot.send_message(
            chat_id=order["user_id"],
            text=f"💰 Возврат по заказу {short_id} оформлен.\nСредства будут возвращены в ближайшее время.",
            parse_mode=None,
        )
    except Exception:
        pass

    try:
        base_text = callback.message.text or callback.message.caption or "Заказ"

        await callback.message.edit_text(
            base_text + f"\n💰 <b>ВОЗВРАТ</b>",
            reply_markup=admin_order_management_keyboard(order_id, "refunded"),
            parse_mode="HTML",
        )
    except Exception:
        pass


# ==================== ОТЗЫВЫ ====================
@dp.callback_query(F.data.startswith("leave_review_"))
async def start_review_for_order(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    order_id = callback.data.replace("leave_review_", "")

    orders = load_orders()
    real_key = find_order_key(orders, order_id)

    if not real_key:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    order = orders[real_key]
    order_id = real_key

    if order["status"] != "completed":
        await callback.answer("❌ Нельзя оставить отзыв для этого заказа", show_alert=True)
        return

    await state.update_data(review_order_id=order_id)

    await callback.message.edit_text(
        f"Оцените покупку:\nЗаказ: {order.get('short_id', order_id)}\nТовар: {order['product']}",
        reply_markup=stars_keyboard(),
    )

    await state.set_state(ReviewStates.waiting_for_stars)


@dp.callback_query(ReviewStates.waiting_for_stars, F.data.startswith("stars_"))
async def process_stars(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    rating = int(callback.data.split("_")[1])
    await state.update_data(stars=rating)

    await callback.message.edit_text(
        f"{'⭐' * rating}\n📸 Отправьте скриншот покупки (необязательно).\n"
        f"Если не хотите, нажмите «Пропустить фото».",
        reply_markup=review_photo_skip_keyboard(),
    )

    await state.set_state(ReviewStates.waiting_for_photo_or_skip)


@dp.callback_query(ReviewStates.waiting_for_photo_or_skip, F.data == "skip_photo")
async def skip_photo(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    await state.update_data(photo=None)
    await callback.message.edit_text("✏️ Напишите текст отзыва:")

    await state.set_state(ReviewStates.waiting_for_text)


@dp.message(ReviewStates.waiting_for_photo_or_skip, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id

    await state.update_data(photo=photo_id)
    await message.answer("✏️ Напишите текст отзыва:")

    await state.set_state(ReviewStates.waiting_for_text)


@dp.message(ReviewStates.waiting_for_text, F.text)
async def process_review_text(message: types.Message, state: FSMContext):
    user_data = await state.get_data()

    stars_str = "⭐" * user_data.get("stars", 5)
    photo_id = user_data.get("photo")
    user_id = message.from_user.id
    order_id = user_data.get("review_order_id")

    review_id = f"rev_{user_id}_{int(datetime.now().timestamp())}"

    reviews = load_reviews()

    reviews[review_id] = {
        "review_id": review_id,
        "user_id": user_id,
        "username": message.from_user.username,
        "full_name": message.from_user.full_name,
        "stars": user_data.get("stars", 5),
        "text": message.text,
        "photo": photo_id,
        "order_id": order_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    }

    save_reviews(reviews)

    if order_id:
        orders = load_orders()
        real_key = find_order_key(orders, order_id)

        if real_key:
            orders[real_key]["reviewed"] = True
            save_orders(orders)

    orders = load_orders()
    real_key = find_order_key(orders, order_id)
    short_id = orders[real_key].get("short_id", order_id) if real_key else order_id

    caption_text = (
        f"НОВЫЙ ОТЗЫВ\n"
        f"ID: {review_id}\n"
        f"От: {message.from_user.full_name}\n"
        f"@{message.from_user.username}\n"
        f"Заказ: {short_id}\n"
        f"Оценка: {stars_str}\n"
        f"Текст: {message.text}"
    )

    try:
        if photo_id:
            await bot.send_photo(
                chat_id=ADMIN_ID,
                photo=photo_id,
                caption=caption_text,
                reply_markup=moderation_keyboard(review_id),
                parse_mode=None,
            )
        else:
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=caption_text,
                reply_markup=moderation_keyboard(review_id),
                parse_mode=None,
            )

        await message.answer(
            "🙏 Спасибо за отзыв!\nОн будет опубликован после проверки.",
            reply_markup=get_main_reply_keyboard(),
        )
    except Exception as e:
        logger.error(f"Ошибка отправки отзыва: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

    await state.clear()


@dp.callback_query(F.data.startswith("approve_"))
async def approve_review(callback: types.CallbackQuery):
    await callback.answer()

    review_id = callback.data.replace("approve_", "")

    reviews = load_reviews()
    review = reviews.get(review_id)

    if not review:
        await callback.answer("❌ Отзыв не найден", show_alert=True)
        return

    channel_text = (
        f"⭐️ НОВЫЙ ОТЗЫВ\n"
        f"Покупатель: @{review.get('username', 'Покупатель')}\n"
        f"Оценка: {'⭐️' * review['stars']}\n"
        f"Отзыв: {review['text']}\n"
        f"Купить: @MaskYoY\n"
        f"Канал: @owerpass_store"
    )

    try:
        photo = review.get("photo")

        if photo:
            await bot.send_photo(CHANNEL_ID, photo, caption=channel_text, parse_mode=None)
        else:
            await bot.send_message(CHANNEL_ID, channel_text, parse_mode=None)

        await bot.send_message(review["user_id"], "🎉 Ваш отзыв опубликован в канале! Спасибо! ⭐")

        review["status"] = "approved"
        save_reviews(reviews)

        if callback.message.caption:
            await callback.message.edit_caption(caption=f"{callback.message.caption}\n✅ ОПУБЛИКОВАН")
        else:
            await callback.message.edit_text(text=f"{callback.message.text}\n✅ ОПУБЛИКОВАН")

        await callback.answer("✅ Отзыв опубликован!", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка публикации: {e}")
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


@dp.callback_query(F.data.startswith("reject_"))
async def reject_review(callback: types.CallbackQuery):
    await callback.answer()

    review_id = callback.data.replace("reject_", "")

    reviews = load_reviews()
    review = reviews.get(review_id)

    if review:
        review["status"] = "rejected"
        save_reviews(reviews)

        try:
            await bot.send_message(review["user_id"], "❌ Ваш отзыв отклонен.\nПо вопросам: @MaskYoY")
        except Exception:
            pass

        try:
            if callback.message.caption:
                await callback.message.edit_caption(caption=f"{callback.message.caption}\n❌ ОТКЛОНЕН")
            else:
                await callback.message.edit_text(text=f"{callback.message.text}\n❌ ОТКЛОНЕН")
        except Exception:
            pass

    await callback.answer("❌ Отзыв отклонен", show_alert=True)


# ==================== ЗАКАЗЫ ПОЛЬЗОВАТЕЛЯ ====================
@dp.callback_query(F.data == "my_orders")
async def show_user_orders_callback(callback: types.CallbackQuery):
    await callback.answer()
    await show_user_orders(callback)


async def show_user_orders(source):
    if isinstance(source, types.CallbackQuery):
        user_id = source.from_user.id
        target = source.message
    else:
        user_id = source.from_user.id
        target = source

    orders = load_orders()
    user_orders = {k: v for k, v in orders.items() if v["user_id"] == user_id}

    if not user_orders:
        text = "📋 У вас пока нет заказов\n🛒 Нажмите «Оформить заказ» чтобы начать!"
        await target.answer(text, reply_markup=main_menu_keyboard())
        return

    kb = InlineKeyboardBuilder()
    text = f"📋 ВАШИ ЗАКАЗЫ ({len(user_orders)} шт.)\n"

    for order_id, order in sorted(user_orders.items(), reverse=True):
        emoji, status_text = STATUS_CONFIG.get(order["status"], ("❓", "Неизвестно"))
        symbol = method_symbol(order.get("payment_method", "uah"))
        short_id = order.get("short_id", order_id[:8])

        if isinstance(order["total"], str):
            total_text = order["total"]
        else:
            total_text = f"{order['total']} {symbol}"

        text += f"{emoji} {short_id}\n📦 {order['product']} x{order['quantity']}\n💰 {total_text}\n📌 {status_text}\n"

        kb.button(text=f"📋 {short_id}", callback_data=f"order_detail_{order_id}")

    kb.button(text="⬅️ Главное меню", callback_data="main_menu")
    kb.adjust(1)

    try:
        await target.edit_text(text, reply_markup=kb.as_markup())
    except Exception:
        await target.answer(text, reply_markup=kb.as_markup())


@dp.callback_query(F.data.startswith("order_detail_"))
async def show_order_detail(callback: types.CallbackQuery):
    await callback.answer()

    order_id = callback.data.replace("order_detail_", "")

    orders = load_orders()
    real_key = find_order_key(orders, order_id)

    if not real_key:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    order = orders[real_key]
    order_id = real_key

    emoji, status_text = STATUS_CONFIG.get(order["status"], ("❓", "Неизвестно"))
    symbol = method_symbol(order.get("payment_method", "uah"))
    short_id = order.get("short_id", order_id[:8])

    if isinstance(order["total"], str):
        total_text = order["total"]
    else:
        total_text = f"{order['total']} {symbol}"

    text = (
        f"📋 ЗАКАЗ {short_id}\n"
        f"Товар: {order['product']}\n"
        f"Количество: {order['quantity']} шт.\n"
        f"Оплата: {method_label(order['payment_method'])}\n"
        f"Сумма: {total_text}\n"
        f"Дата: {datetime.fromisoformat(order['created_at']).strftime('%d.%m.%Y %H:%M')}\n"
        f"Статус: {emoji} {status_text}\n"
    )

    if order.get("phone"):
        text += f"\nНомер: {order['phone']}\n"

    if order["status"] == "completed":
        kb = user_order_actions_keyboard(order_id)
    elif order["status"] in ["phone_sent", "code_sent"]:
        kb = user_number_actions_keyboard(order_id)
    elif order["status"] == "awaiting_payment":
        kb = awaiting_payment_keyboard(order_id)
    else:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text="📋 Все заказы", callback_data="my_orders")
        kb_builder.button(text="⬅️ Главное меню", callback_data="main_menu")
        kb_builder.adjust(1)
        kb = kb_builder.as_markup()

    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


@dp.callback_query(F.data.startswith("user_replace_"))
async def request_replace(callback: types.CallbackQuery):
    await callback.answer()

    order_id = callback.data.replace("user_replace_", "")

    orders = load_orders()
    real_key = find_order_key(orders, order_id)

    if not real_key:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    order = orders[real_key]
    short_id = order.get("short_id", real_key)

    await bot.send_message(
        ADMIN_ID,
        f"🔄 ЗАПРОС НА ЗАМЕНУ!\nЗаказ: {short_id}\nОт: @{callback.from_user.username}",
        parse_mode=None,
    )

    await callback.message.answer(
        "🔄 Запрос на замену отправлен!\nПродавец свяжется с вами.\n📞 @MaskYoY"
    )


@dp.callback_query(F.data.startswith("user_refund_"))
async def request_refund(callback: types.CallbackQuery):
    await callback.answer()

    order_id = callback.data.replace("user_refund_", "")

    orders = load_orders()
    real_key = find_order_key(orders, order_id)

    if not real_key:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    order = orders[real_key]
    short_id = order.get("short_id", real_key)

    await bot.send_message(
        ADMIN_ID,
        f"💰 ЗАПРОС НА ВОЗВРАТ!\nЗаказ: {short_id}\nОт: @{callback.from_user.username}",
        parse_mode=None,
    )

    await callback.message.answer(
        "💰 Запрос на возврат отправлен!\nАдминистрация рассмотрит запрос.\n📞 @MaskYoY"
    )


# ==================== ПОДДЕРЖКА ====================
@dp.callback_query(F.data.startswith("support_"))
async def start_support_chat(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    order_id = callback.data.replace("support_", "")

    orders = load_orders()
    real_key = find_order_key(orders, order_id)

    if real_key:
        order_id = real_key

    await state.update_data(support_order_id=order_id)
    await state.set_state(SupportStates.chatting)

    close_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Закрыть чат")]],
        resize_keyboard=True,
    )

    await callback.message.answer(
        "🆘 Напишите ваше сообщение (текст, фото или скриншот оплаты) — оно будет отправлено продавцу.\n"
        "Продавец ответит вам в этом же чате. Чтобы закрыть чат, нажмите кнопку ниже.",
        reply_markup=close_kb,
    )


@dp.message(SupportStates.chatting, F.text == "❌ Закрыть чат")
async def close_support_chat(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Чат поддержки закрыт.", reply_markup=get_main_reply_keyboard())


@dp.message(SupportStates.chatting, F.text | F.photo | F.document | F.video | F.animation)
async def relay_user_to_admin(message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("support_order_id", "не указан")

    orders = load_orders()
    real_key = find_order_key(orders, order_id)
    short_id = orders[real_key].get("short_id", order_id) if real_key else order_id

    header = (
        f"🆘 СООБЩЕНИЕ ОТ ПОКУПАТЕЛЯ\n"
        f"Заказ: {short_id}\n"
        f"От: @{message.from_user.username or 'без имени'}\n"
        f"↳ Ответьте (Ответ) на это сообщение, чтобы ответ дошёл покупателю."
    )

    try:
        await bot.send_message(chat_id=ADMIN_ID, text=header, parse_mode=None)

        forwarded = await bot.copy_message(
            chat_id=ADMIN_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )

        relay = load_relay()
        relay[str(forwarded.message_id)] = message.from_user.id
        save_relay(relay)

        chat_history = load_chat_history()

        if real_key not in chat_history:
            chat_history[real_key] = []

        chat_history[real_key].append({
            "sender": "user",
            "text": message.text or f"[{message.content_type}]",
            "date": datetime.now().isoformat(),
        })

        save_chat_history(chat_history)

        await message.answer("✅ Сообщение отправлено продавцу. Ожидайте ответа здесь же.")
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить сообщение: {e}")


@dp.message(SupportStates.chatting, ~F.text & ~F.photo & ~F.document & ~F.video & ~F.animation)
async def relay_ignore_other(message: types.Message):
    await message.answer("⚠️ Пожалуйста, отправьте текст, фото или документ. Другие типы сообщений не пересылаются.")


@dp.message(F.from_user.id == ADMIN_ID, F.reply_to_message)
async def relay_admin_to_user(message: types.Message):
    relay = load_relay()
    replied_id = str(message.reply_to_message.message_id)
    user_id = relay.get(replied_id)

    if not user_id:
        return

    try:
        await bot.copy_message(
            chat_id=user_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )

        await message.answer("✅ Ответ доставлен покупателю")
    except Exception as e:
        await message.answer(f"❌ Не удалось доставить ответ: {e}")


# ==================== ЗАПРОС КОДА ПОКУПАТЕЛЕМ ====================
@dp.callback_query(F.data.startswith("user_request_code_"))
async def user_request_code(callback: types.CallbackQuery):
    await callback.answer()

    order_id = callback.data.replace("user_request_code_", "")

    orders = load_orders()
    real_key = find_order_key(orders, order_id)

    if not real_key:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    order = orders[real_key]
    order_id = real_key

    if not order.get("phone"):
        await callback.answer("❌ Номер еще не отправлен", show_alert=True)
        return

    short_id = order.get("short_id", order_id)

    admin_msg = (
        f"🔑 ЗАПРОС КОДА!\n"
        f"Заказ: {short_id}\n"
        f"Покупатель: @{order['username']}\n"
        f"Номер: {order['phone']}\n"
        f"Отправьте код подтверждения"
    )

    await bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_msg,
        reply_markup=InlineKeyboardBuilder().button(
            text="🔑 Отправить код",
            callback_data=f"admin_send_code_{order_id}",
        ).as_markup(),
        parse_mode=None,
    )

    await callback.message.answer(
        "🔑 Запрос кода отправлен!\nПродавец отправит код в течение 1-2 минут.\nОжидайте..."
    )


@dp.callback_query(F.data.startswith("user_confirm_login_"))
async def user_confirm_login(callback: types.CallbackQuery):
    await callback.answer()

    order_id = callback.data.replace("user_confirm_login_", "")

    orders = load_orders()
    real_key = find_order_key(orders, order_id)

    if not real_key:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    order = orders[real_key]
    order_id = real_key

    if order.get("status") == "completed":
        await callback.answer("✅ Заказ уже выполнен", show_alert=True)
        return

    order["status"] = "completed"
    order["completed_at"] = datetime.now().isoformat()
    order["reminder_sent"] = False
    save_orders(orders)

    users = load_users()
    user_key = str(order["user_id"])

    if user_key in users:
        users[user_key]["total_spent"] = users[user_key].get("total_spent", 0) + (
            order.get("total", 0) if not isinstance(order.get("total", 0), str) else 0
        )
        users[user_key]["orders_count"] = users[user_key].get("orders_count", 0) + 1

    save_users(users)

    if users[user_key].get("referred_by"):
        await process_referral_bonus(
            users[user_key]["referred_by"],
            order["user_id"],
            order.get("total", 0),
        )

    short_id = order.get("short_id", order_id)

    await bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            f"✅ ПОКУПАТЕЛЬ ПОДТВЕРДИЛ ВХОД!\n"
            f"Заказ: {short_id}\n"
            f"Товар: {order['product']}\n"
            f"Номер: {order.get('phone', 'Н/Д')}"
        ),
        parse_mode=None,
    )

    client_msg = (
        f"🎉 ЗАКАЗ ВЫПОЛНЕН!\n"
        f"Заказ: {short_id}\n"
        f"Товар: {order['product']}\n"
        f"Номер: {order.get('phone', 'Н/Д')}\n"
        f"Пожалуйста, оставьте отзыв о покупке!\n"
        f"Спасибо за покупку!"
    )

    try:
        await bot.send_message(
            chat_id=order["user_id"],
            text=client_msg,
            reply_markup=user_order_actions_keyboard(order_id),
            parse_mode=None,
        )
    except Exception:
        pass

    asyncio.create_task(schedule_reminder(order_id))

    try:
        await callback.message.edit_text(f"{callback.message.text}\n✅ Вход подтвержден!")
    except Exception:
        await callback.message.answer("✅ Вход подтвержден!")


# ==================== ПОЛЬЗОВАТЕЛЬСКИЕ КНОПКИ ====================
@dp.message(F.from_user.id != ADMIN_ID, F.text == "🛍 Каталог")
async def catalog_from_keyboard(message: types.Message, state: FSMContext):
    if not await check_subscription(message.from_user.id):
        await message.answer("⚠️ Подпишитесь на канал!", reply_markup=subscribe_keyboard())
        return

    await state.clear()
    await message.answer("📂 Выберите категорию:", reply_markup=catalog_keyboard())


@dp.message(F.from_user.id != ADMIN_ID, F.text == "💬 Отзывы")
async def reviews_from_keyboard(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await message.answer("⚠️ Подпишитесь на канал!", reply_markup=subscribe_keyboard())
        return

    await message.answer(
        "💬 Отзывы покупателей\nЗдесь вы можете посмотреть отзывы о нашем магазине.",
        reply_markup=reviews_keyboard(),
    )


@dp.message(F.from_user.id != ADMIN_ID, F.text == "📋 Мои заказы")
async def my_orders_from_keyboard(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await message.answer("⚠️ Подпишитесь на канал!", reply_markup=subscribe_keyboard())
        return

    await show_user_orders(message)


@dp.message(F.from_user.id != ADMIN_ID, F.text == "❓ Частые вопросы")
async def faq_from_keyboard(message: types.Message):
    await message.answer(FAQ_TEXT, reply_markup=get_main_reply_keyboard())


@dp.message(F.from_user.id != ADMIN_ID, F.text == "📢 Наш Канал")
async def channel_from_keyboard(message: types.Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="📢 Перейти в канал", url="http://t.me/owerpass_store")
    await message.answer("Нажмите кнопку для перехода в канал:", reply_markup=kb.as_markup())


@dp.message(F.from_user.id != ADMIN_ID, F.text == "🛒 Оформить заказ")
async def order_from_keyboard(message: types.Message, state: FSMContext):
    if not await check_subscription(message.from_user.id):
        await message.answer("⚠️ Подпишитесь на канал!", reply_markup=subscribe_keyboard())
        return

    await state.clear()
    await message.answer("📂 Выберите категорию товара:", reply_markup=catalog_keyboard())
    await state.set_state(OrderStates.waiting_for_category)


@dp.callback_query(F.data == "check_sub")
async def process_check_sub(callback: types.CallbackQuery):
    await callback.answer()

    if await check_subscription(callback.from_user.id):
        try:
            await callback.message.edit_text("🎉 Спасибо за подписку!", reply_markup=main_menu_keyboard())
        except Exception:
            await callback.message.answer("🎉 Спасибо за подписку!", reply_markup=main_menu_keyboard())

        await callback.message.answer(
            "Используйте кнопки на панели для навигации:",
            reply_markup=get_main_reply_keyboard(),
        )
    else:
        await callback.answer("❌ Вы не подписались!", show_alert=True)


@dp.callback_query(F.data == "main_menu")
async def go_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()

    try:
        await callback.message.edit_text("👋 Главное меню:", reply_markup=main_menu_keyboard())
    except Exception:
        await callback.message.answer("👋 Главное меню:", reply_markup=main_menu_keyboard())


@dp.callback_query(F.data == "menu_catalog")
async def open_catalog(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()

    try:
        await callback.message.edit_text("📂 Выберите категорию:", reply_markup=catalog_keyboard())
    except Exception:
        await callback.message.answer("📂 Выберите категорию:", reply_markup=catalog_keyboard())


@dp.callback_query(F.data == "menu_reviews")
async def open_reviews_menu(callback: types.CallbackQuery):
    await callback.answer()

    try:
        await callback.message.edit_text("💬 Отзывы покупателей", reply_markup=reviews_keyboard())
    except Exception:
        await callback.message.answer("💬 Отзывы покупателей", reply_markup=reviews_keyboard())


@dp.callback_query(F.data == "show_faq")
async def show_faq(callback: types.CallbackQuery):
    await callback.answer()

    try:
        await callback.message.edit_text(FAQ_TEXT, reply_markup=main_menu_keyboard())
    except Exception:
        await callback.message.answer(FAQ_TEXT, reply_markup=main_menu_keyboard())


@dp.callback_query(F.data.startswith("cat_"))
async def show_category(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    category = callback.data.replace("cat_", "")

    if category not in CATEGORIES:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return

    try:
        await callback.message.edit_text(
            f"{CATEGORIES[category]['name']}\nВыберите товар:",
            reply_markup=category_products_keyboard(category),
        )
    except Exception:
        await callback.message.answer(
            f"{CATEGORIES[category]['name']}\nВыберите товар:",
            reply_markup=category_products_keyboard(category),
        )


@dp.callback_query(F.data.startswith("product_"))
async def process_product_selection(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    parts = callback.data.split("_", 2)

    if len(parts) < 3:
        await callback.answer("❌ Ошибка данных", show_alert=True)
        return

    category = parts[1]
    clean_product = parts[2]
    full_product_name = None

    for p_name in CATEGORIES[category]["products"].keys():
        clean_p_name = p_name

        for emoji in [
            "🇲🇲", "🇺🇸", "🇨🇴", "🇧🇩", "🇫🇷", "🇧🇷", "🇺🇿", "🇹🇭",
            "🇬🇧", "🇺🇦", "🇧🇾", "🇰🇿", "🇵🇱", "🇷🇺", "🇩🇪", "🇨🇦",
            "🇭🇺", "🇬🇱",
        ]:
            if p_name.startswith(emoji):
                clean_p_name = p_name[len(emoji):].strip()
                break

        if clean_p_name == clean_product:
            full_product_name = p_name
            break

    if not full_product_name or category not in CATEGORIES or full_product_name not in CATEGORIES[category]["products"]:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    await state.update_data(category=category, product=full_product_name)

    try:
        await callback.message.edit_text(
            f"✅ Выбрано: {full_product_name}\n🔢 Выберите количество:",
            reply_markup=quantity_keyboard(),
        )
    except Exception:
        await callback.message.answer(
            f"✅ Выбрано: {full_product_name}\n🔢 Выберите количество:",
            reply_markup=quantity_keyboard(),
        )

    await state.set_state(OrderStates.waiting_for_quantity)


async def ask_payment_method(target, state: FSMContext):
    data = await state.get_data()

    category = data["category"]
    product = data["product"]
    quantity = data["quantity"]

    price_data = CATEGORIES[category]["products"][product]
    can_nft = price_data.get("nft", False)

    uah_price = price_data["uah"]
    stars_price = price_data["stars"]

    if isinstance(uah_price, str):
        uah_total = uah_price
    else:
        uah_total = uah_price * quantity

    stars_total = stars_price * quantity

    user_level = get_user_level(target.from_user.id if hasattr(target, "from_user") else 0)
    discount_percent = user_level.get("discount", 0)
    discount_text = ""

    if discount_percent > 0 and isinstance(uah_total, (int, float)):
        discount_amount = uah_total * (discount_percent / 100)
        uah_total = uah_total - discount_amount
        discount_text = f"\n🎁 Ваша скидка {discount_percent}%: -{discount_amount:.0f}₴"

    if isinstance(uah_total, str):
        uah_total_text = uah_total
    else:
        uah_total_text = f"{uah_total:.2f}"

    text = (
        f"📦 Товар: {product}\n"
        f"🔢 Количество: {quantity} шт.\n"
        f"💱 ВЫБЕРИТЕ СПОСОБ ОПЛАТЫ:\n"
        f"💳 Гривны: {uah_total_text} ₴\n"
        f"⭐ Звёзды: {stars_total} ⭐"
    )

    if can_nft:
        text += f"\n🖼 NFT: {stars_total} ⭐ (эквивалент)"

    if discount_text:
        text += discount_text

    text += "\n⬇️ Нажмите кнопку ниже:"

    try:
        await target.edit_text(text, reply_markup=payment_method_keyboard(can_nft))
    except Exception:
        await target.answer(text, reply_markup=payment_method_keyboard(can_nft))


@dp.callback_query(OrderStates.waiting_for_quantity, F.data.startswith("qty_"))
async def process_quantity(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    if callback.data == "qty_custom":
        try:
            await callback.message.edit_text("✏️ Введите количество числом:")
        except Exception:
            await callback.message.answer("✏️ Введите количество числом:")

        await state.set_state(OrderStates.waiting_for_custom_quantity)
        return

    quantity = int(callback.data.split("_")[1])
    await state.update_data(quantity=quantity)

    await ask_payment_method(callback.message, state)
    await state.set_state(OrderStates.waiting_for_payment_method)


@dp.message(OrderStates.waiting_for_custom_quantity)
async def process_custom_quantity(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) <= 0:
        await message.answer("❌ Введите корректное число!")
        return

    quantity = int(message.text)
    await state.update_data(quantity=quantity)

    await ask_payment_method(message, state)
    await state.set_state(OrderStates.waiting_for_payment_method)


async def show_order_confirmation(callback: types.CallbackQuery, state: FSMContext):
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

        user_level = get_user_level(callback.from_user.id)
        discount_percent = user_level.get("discount", 0)
        discount_amount = total * (discount_percent / 100)
        total = total - discount_amount

    symbol = method_symbol(method)

    promo_code = data.get("promo_code")

    if promo_code and isinstance(total, (int, float)):
        promo_codes = load_promo_codes()
        promo = promo_codes.get(promo_code.upper())

        if promo and promo.get("is_active", True):
            expired = False

            if promo.get("expires_at"):
                expires = datetime.fromisoformat(promo["expires_at"])
                if datetime.now() > expires:
                    expired = True

            if not expired:
                if promo["discount_type"] == "percent":
                    promo_discount = total * (promo["discount_value"] / 100)
                    total = total - promo_discount
                    discount_amount += promo_discount
                elif promo["discount_type"] == "fixed":
                    promo_discount = min(promo["discount_value"], total)
                    total = total - promo_discount
                    discount_amount += promo_discount

    if isinstance(total, str):
        total_text = f"{total} {symbol}"
    else:
        total_text = f"{total:.2f} {symbol}"

    text = (
        f"📋 ПОДТВЕРЖДЕНИЕ ЗАКАЗА\n"
        f"Товар: {product}\n"
        f"Количество: {quantity} шт.\n"
        f"Способ оплаты: {method_label(method)}\n"
        f"Сумма к оплате: {total_text}\n"
    )

    if discount_amount > 0:
        text += f"🎁 Скидки: -{discount_amount:.2f} {symbol}\n"

    text += f"\nВсё верно?"

    try:
        await callback.message.edit_text(text, reply_markup=confirm_order_keyboard())
    except Exception:
        await callback.message.answer(text, reply_markup=confirm_order_keyboard())

    await state.set_state(OrderStates.waiting_for_confirmation)


@dp.callback_query(OrderStates.waiting_for_payment_method, F.data.startswith("pay_"))
async def process_payment_method(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    method = callback.data.replace("pay_", "")
    await state.update_data(payment_method=method)

    await show_order_confirmation(callback, state)


@dp.callback_query(OrderStates.waiting_for_confirmation, F.data == "edit_quantity")
async def edit_quantity_cb(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    try:
        await callback.message.edit_text("🔢 Выберите количество:", reply_markup=quantity_keyboard())
    except Exception:
        await callback.message.answer("🔢 Выберите количество:", reply_markup=quantity_keyboard())

    await state.set_state(OrderStates.waiting_for_quantity)


@dp.callback_query(OrderStates.waiting_for_confirmation, F.data == "edit_payment_method")
async def edit_payment_method_cb(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await ask_payment_method(callback.message, state)
    await state.set_state(OrderStates.waiting_for_payment_method)


@dp.callback_query(OrderStates.waiting_for_confirmation, F.data == "apply_promo_at_checkout")
async def apply_promo_at_checkout_cb(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text("🎟 Введите промокод:")
    await state.set_state(CheckoutPromoStates.waiting_for_promo_code)


@dp.message(CheckoutPromoStates.waiting_for_promo_code, F.text)
async def process_promo_at_checkout(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()

    promo_codes = load_promo_codes()
    promo = promo_codes.get(code)

    if not promo:
        await message.answer("❌ Промокод не найден")
        await state.clear()
        return

    if not promo.get("is_active", True):
        await message.answer("❌ Промокод неактивен")
        await state.clear()
        return

    if promo.get("max_uses") and promo.get("current_uses", 0) >= promo["max_uses"]:
        await message.answer("❌ Промокод исчерпан")
        await state.clear()
        return

    if promo.get("expires_at"):
        expires = datetime.fromisoformat(promo["expires_at"])
        if datetime.now() > expires:
            await message.answer("❌ Срок действия промокода истёк")
            await state.clear()
            return

    await state.update_data(promo_code=code)
    await message.answer(f"✅ Промокод <code>{code}</code> применён!", parse_mode="HTML")

    data = await state.get_data()

    class FakeCallback:
        def __init__(self, message, data):
            self.message = message
            self.from_user = message.from_user
            self.data = data

        async def answer(self):
            pass

    fake_cb = FakeCallback(message, "confirm_order")
    await show_order_confirmation(fake_cb, state)


@dp.callback_query(OrderStates.waiting_for_confirmation, F.data == "confirm_order")
async def confirm_order_cb(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await create_order(callback, state)


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
                if promo["discount_type"] == "percent":
                    promo_discount = total * (promo["discount_value"] / 100)
                    total = total - promo_discount
                    discount_amount += promo_discount
                elif promo["discount_type"] == "fixed":
                    promo_discount = min(promo["discount_value"], total)
                    total = total - promo_discount
                    discount_amount += promo_discount

                promo["current_uses"] = promo.get("current_uses", 0) + 1
                promo_codes[promo_code.upper()] = promo
                save_promo_codes(promo_codes)

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
        "status": "awaiting_payment",
        "created_at": datetime.now().isoformat(),
        "phone": None,
        "code": None,
        "reviewed": False,
        "reminder_sent": False,
    }

    save_orders(orders)

    if isinstance(total, str):
        total_display = total
    else:
        total_display = f"{total:.2f} {symbol}"

    admin_msg = (
        f"📱 НОВЫЙ ЗАКАЗ {short_id}\n"
        f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        f"Покупатель: @{username} | {user_full_name}\n"
        f"ID: {user_id}\n"
        f"📂 Категория: {category_name}\n"
        f"📦 Товар: {product}\n"
        f"🔢 Количество: {quantity} шт.\n"
        f"💳 Оплата: {method_label(method)}\n"
        f"💰 Сумма: {total_display}\n"
    )

    if discount_amount > 0:
        admin_msg += f"🎁 Скидки: -{discount_amount:.2f} {symbol}\n"

    admin_msg += f"\nСтатус: ⏳ Ожидает оплаты"

    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_msg,
            reply_markup=admin_order_management_keyboard(legacy_order_id, "awaiting_payment"),
            parse_mode=None,
        )
    except Exception as e:
        logger.error(f"Failed to send admin notification: {e}")

    requisites = get_requisites(method)

    payment_msg = (
        f"✅ ЗАКАЗ {short_id} СОЗДАН!\n"
        f"📂 Категория: {category_name}\n"
        f"📦 Товар: {product}\n"
        f"🔢 Количество: {quantity} шт.\n"
        f"💳 Способ оплаты: {method_label(method)}\n"
        f"💰 Сумма: {total_display}\n"
    )

    if discount_amount > 0:
        payment_msg += f"🎁 Скидки: -{discount_amount:.2f} {symbol}\n"

    payment_msg += (
        f"\n📌 РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ:\n"
        f"{requisites}\n"
        f"После оплаты нажмите кнопку связи с продавцом.\n"
        f"Если ЛС не открываются — «🆘 Написать в боте»"
    )

    try:
        await target.edit_text(payment_msg, reply_markup=awaiting_payment_keyboard(legacy_order_id), parse_mode=None)
    except Exception:
        await target.answer(payment_msg, reply_markup=awaiting_payment_keyboard(legacy_order_id), parse_mode=None)

    await state.clear()


# ==================== ПРОФИЛЬ / РЕФЕРАЛЫ / ПРОМОКОДЫ ====================
@dp.message(F.from_user.id != ADMIN_ID, F.text == "👤 Профиль")
@dp.callback_query(F.data == "profile_menu")
async def show_profile(event, state: FSMContext = None):
    if isinstance(event, types.CallbackQuery):
        await event.answer()
        message = event.message
        user_id = event.from_user.id
        user_obj = event.from_user
    else:
        message = event
        user_id = event.from_user.id
        user_obj = event.from_user

    if user_id == ADMIN_ID:
        return

    users = load_users()
    level = get_user_level(user_id)

    orders = load_orders()
    user_orders = [o for o in orders.values() if o["user_id"] == user_id]
    completed_orders = [o for o in user_orders if o["status"] == "completed"]

    total_spent = 0.0

    for o in completed_orders:
        if not isinstance(o.get("total", 0), str):
            total_spent += float(o.get("total", 0))

    referrals = load_referrals()
    ref_data = referrals.get(str(user_id), {})
    total_referrals = len(ref_data.get("referrals_list", []))

    text = (
        f"👤 <b>Ваш профиль</b>\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"👤 Имя: {user_obj.full_name}\n"
        f"📧 Имя пользователя: @{user_obj.username or 'не указано'}\n"
        f"⭐ <b>Уровень:</b> {level['emoji']} {level['name']}\n"
        f"🎁 Скидка: {level['discount']}%\n"
        f"💵 Потрачено: {total_spent:.2f} грн\n"
        f"📦 Покупок: {len(completed_orders)}\n"
    )

    levels_order = ["Бронза", "Серебро", "Золото", "Платина", "VIP"]
    current_idx = levels_order.index(level["name"]) if level["name"] in levels_order else 0

    if current_idx < len(levels_order) - 1:
        next_level = levels_order[current_idx + 1]

        level_keys = {
            "Серебро": ("level_silver_min", 500),
            "Золото": ("level_gold_min", 1500),
            "Платина": ("level_platinum_min", 3000),
            "VIP": ("level_vip_min", 5000),
        }

        key, default = level_keys.get(next_level, ("level_silver_min", 500))
        next_min = get_setting(key, default)

        remaining = max(0, next_min - total_spent)
        progress = min(100, (total_spent / next_min) * 100) if next_min > 0 else 100

        text += (
            f"📈 <b>До уровня {next_level}:</b>\n"
            f"{'█' * int(progress / 5)}{'░' * (20 - int(progress / 5))} {progress:.0f}%\n"
            f"Осталось: {remaining:.2f} грн\n"
        )

    text += (
        f"👥 <b>Рефералы:</b> {total_referrals}\n"
        f"💸 Сумма бонусов: {ref_data.get('total_earned', 0):.2f} грн"
    )

    kb = profile_keyboard()

    if isinstance(event, types.CallbackQuery):
        try:
            await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@dp.message(F.from_user.id != ADMIN_ID, F.text == "👥 Рефералы")
@dp.callback_query(F.data == "referral_menu")
async def show_referral_menu(event):
    if isinstance(event, types.CallbackQuery):
        await event.answer()
        message = event.message
        user_id = event.from_user.id
    else:
        message = event
        user_id = event.from_user.id

    if user_id == ADMIN_ID:
        return

    referrals = load_referrals()
    ref_data = referrals.get(str(user_id), {})

    if "referral_code" not in ref_data or not ref_data.get("referral_code"):
        code = hashlib.md5(f"{user_id}_ref_salt".encode()).hexdigest()[:8].upper()
        ref_data["referral_code"] = code

    if "referrals_list" not in ref_data:
        ref_data["referrals_list"] = []

    if "total_earned" not in ref_data:
        ref_data["total_earned"] = 0

    referrals[str(user_id)] = ref_data
    save_referrals(referrals)

    code = ref_data["referral_code"]
    bot_info = await bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start=ref_{code}"

    total_referrals = len(ref_data.get("referrals_list", []))
    total_earned = ref_data.get("total_earned", 0)
    bonus_percent = get_setting("referral_bonus_percent", 5.0)

    text = (
        f"👥 <b>Реферальная программа</b>\n"
        f"Приглашайте друзей и получайте бонусы!\n"
        f"🎁 <b>Ваш бонус:</b> {bonus_percent}% с первой покупки каждого реферала\n"
        f"Бонус выдаётся одноразовым промокодом.\n\n"
        f"📊 <b>Ваша статистика:</b>\n"
        f"• Приглашено: {total_referrals}\n"
        f"• Сумма бонусов: {total_earned:.2f} грн\n"
        f"🔗 <b>Ваша ссылка:</b>\n<code>{referral_link}</code>\n"
        f"Или ваш код: <code>{code}</code>"
    )

    if isinstance(event, types.CallbackQuery):
        try:
            await message.edit_text(text, reply_markup=referral_menu_keyboard(), parse_mode="HTML")
        except Exception:
            await message.answer(text, reply_markup=referral_menu_keyboard(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=referral_menu_keyboard(), parse_mode="HTML")


@dp.callback_query(F.data == "referral_stats")
async def show_referral_stats(callback: types.CallbackQuery):
    await callback.answer()

    referrals = load_referrals()
    ref_data = referrals.get(str(callback.from_user.id), {})

    text = f"📊 <b>Детальная статистика рефералов</b>\n"

    ref_list = ref_data.get("referrals_list", [])

    if not ref_list:
        text += "<i>У вас пока нет рефералов</i>"
    else:
        text += f"Всего рефералов: {len(ref_list)}\n"

        for ref in ref_list[-10:]:
            status = "✅ Купил" if ref.get("first_purchase_done") else "⏳ Еще не купил"
            date = datetime.fromisoformat(ref["date"]).strftime("%d.%m.%Y")

            text += f"👤 @{ref.get('username', 'неизвестно')}\n"
            text += f"   {status}"

            if ref.get("bonus_promo_code"):
                text += f" (промокод {ref['bonus_promo_code']})"
            elif ref.get("bonus_amount", 0) > 0:
                text += f" (+{ref['bonus_amount']:.2f} грн)"

            text += f"\n📅 {date}\n"

    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="referral_menu")

    try:
        await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")


@dp.message(F.from_user.id != ADMIN_ID, F.text == "🎟 Промокод")
@dp.callback_query(F.data == "promo_menu")
async def show_promo_menu(event, state: FSMContext = None):
    if isinstance(event, types.CallbackQuery):
        await event.answer()
        message = event.message

        if event.from_user.id == ADMIN_ID:
            return
    else:
        message = event

        if event.from_user.id == ADMIN_ID:
            return

    text = "🎟 <b>Промокоды</b>\nВведите ваш промокод:"

    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="main_menu")

    if isinstance(event, types.CallbackQuery):
        try:
            await message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
        except Exception:
            await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")

    if state:
        await state.set_state(PromoStates.waiting_for_promo_code)


@dp.message(PromoStates.waiting_for_promo_code, F.text)
async def process_user_promo(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        return

    if message.text.startswith("/"):
        await state.clear()
        return

    code = message.text.strip().upper()

    promo_codes = load_promo_codes()
    promo = promo_codes.get(code)

    if not promo:
        await message.answer("❌ Промокод не найден")
        await state.clear()
        return

    if not promo.get("is_active", True):
        await message.answer("❌ Промокод неактивен")
        await state.clear()
        return

    if promo.get("max_uses") and promo.get("current_uses", 0) >= promo["max_uses"]:
        await message.answer("❌ Промокод исчерпан")
        await state.clear()
        return

    if promo.get("expires_at"):
        expires = datetime.fromisoformat(promo["expires_at"])
        if datetime.now() > expires:
            await message.answer("❌ Срок действия промокода истёк")
            await state.clear()
            return

    if promo["discount_type"] == "percent":
        desc = f"{promo['discount_value']}% скидки"
    else:
        desc = f"{promo['discount_value']} грн скидки"

    await message.answer(
        f"✅ Промокод <code>{code}</code> принят!\n"
        f"🎁 {desc}\n"
        f"Он будет применён при следующем оформлении заказа.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )

    await state.clear()


# ==================== ПОВТОР ЗАКАЗА ====================
@dp.callback_query(F.data == "repeat_last_order")
async def repeat_last_order(callback: types.CallbackQuery):
    await callback.answer()

    orders = load_orders()

    user_orders = [
        o for o in orders.values()
        if o["user_id"] == callback.from_user.id and o["status"] == "completed"
    ]

    if not user_orders:
        await callback.message.answer("❌ У вас пока нет завершённых заказов")
        return

    last_order = max(user_orders, key=lambda x: x.get("completed_at", x.get("created_at", "")))

    text = (
        f"🔁 <b>Повторить последний заказ?</b>\n"
        f"📦 Товар: {last_order['product']}\n"
        f"🔢 Количество: {last_order['quantity']} шт.\n"
        f"💰 Сумма: {last_order['total']} грн"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, повторить", callback_data=f"confirm_repeat_{last_order['order_id']}")
    kb.button(text="❌ Нет", callback_data="main_menu")
    kb.adjust(1)

    try:
        await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")


@dp.callback_query(F.data.startswith("repeat_order_"))
async def repeat_specific_order(callback: types.CallbackQuery):
    await callback.answer()

    order_id = callback.data.replace("repeat_order_", "")

    orders = load_orders()
    real_key = find_order_key(orders, order_id)

    if not real_key:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    order = orders[real_key]
    order_id = real_key

    text = (
        f"🔁 <b>Повторить заказ?</b>\n"
        f"📦 Товар: {order['product']}\n"
        f"🔢 Количество: {order['quantity']} шт.\n"
        f"💰 Сумма: {order['total']} грн"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, повторить", callback_data=f"confirm_repeat_{order_id}")
    kb.button(text="❌ Нет", callback_data="main_menu")
    kb.adjust(1)

    try:
        await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")


@dp.callback_query(F.data.startswith("confirm_repeat_"))
async def confirm_repeat_order(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    old_order_id = callback.data.replace("confirm_repeat_", "")

    orders = load_orders()
    real_key = find_order_key(orders, old_order_id)

    if not real_key:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    order = orders[real_key]

    await state.update_data(
        category=order["category"],
        product=order["product"],
        quantity=order["quantity"],
    )

    await ask_payment_method(callback.message, state)
    await state.set_state(OrderStates.waiting_for_payment_method)


# ==================== АДМИН: ПАНЕЛЬ УПРАВЛЕНИЯ ====================
@dp.message(F.from_user.id == ADMIN_ID, F.text == "📈 Панель управления")
async def admin_dashboard(message: types.Message):
    await show_admin_dashboard(message)


@dp.callback_query(F.from_user.id == ADMIN_ID, F.data.in_(["admin_dashboard_refresh", "admin_orders_dashboard"]))
async def admin_dashboard_callback(callback: types.CallbackQuery):
    await callback.answer()

    if callback.data == "admin_orders_dashboard":
        await show_admin_orders_page(callback.message, 0, edit=True)
    else:
        await show_admin_dashboard(callback.message, edit=True)


async def show_admin_dashboard(target, edit: bool = False):
    orders = load_orders()
    users = load_users()

    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    revenue_today = 0
    revenue_yesterday = 0
    revenue_week = 0
    revenue_month = 0
    total_revenue = 0
    total_orders = 0
    completed_orders = 0
    product_stats = {}

    for order in orders.values():
        if order["status"] == "completed" and order.get("completed_at"):
            try:
                completed_dt = datetime.fromisoformat(order["completed_at"])
            except Exception:
                continue

            amount = order.get("total", 0)

            if isinstance(amount, str):
                continue

            total_revenue += amount
            completed_orders += 1

            if completed_dt >= today:
                revenue_today += amount
            elif completed_dt >= yesterday:
                revenue_yesterday += amount

            if completed_dt >= week_ago:
                revenue_week += amount

            if completed_dt >= month_ago:
                revenue_month += amount

            product = order["product"]
            product_stats[product] = product_stats.get(product, 0) + 1
            total_orders += 1

    new_users_today = sum(
        1 for u in users.values()
        if u.get("first_seen") and datetime.fromisoformat(u["first_seen"]) >= today
    )

    repeat_customers = sum(1 for u in users.values() if u.get("orders_count", 0) > 1)
    conversion = (completed_orders / len(users) * 100) if users else 0
    avg_check = total_revenue / completed_orders if completed_orders > 0 else 0

    top_product = "Нет"

    if product_stats:
        top_product = max(product_stats.items(), key=lambda x: x[1])[0]

    sources = load_traffic_sources()
    best_source = "Нет"
    best_revenue = 0

    for name, data in sources.items():
        if data.get("total_revenue", 0) > best_revenue:
            best_revenue = data["total_revenue"]
            best_source = name

    text = (
        f"📊 <b>Панель управления OverPass Store</b>\n"
        f"💰 <b>Прибыль сегодня:</b> {revenue_today:.2f} грн\n"
        f"💰 <b>Прибыль вчера:</b> {revenue_yesterday:.2f} грн\n"
        f"💰 <b>За неделю:</b> {revenue_week:.2f} грн\n"
        f"💰 <b>За месяц:</b> {revenue_month:.2f} грн\n"
        f"👥 <b>Новых пользователей сегодня:</b> {new_users_today}\n"
        f"♻️ <b>Повторных покупок:</b> {repeat_customers}\n"
        f"📈 <b>Конверсия:</b> {conversion:.2f}%\n"
        f"💵 <b>Средний чек:</b> {avg_check:.2f} грн\n"
        f"📊 <b>Общий оборот:</b> {total_revenue:.2f} грн\n"
        f"⭐ <b>ТОП товар:</b> {top_product}\n"
        f"🔥 <b>Лучший источник:</b> {best_source} ({best_revenue:.2f} грн)\n"
        f"👤 Всего пользователей: {len(users)}\n"
        f"📦 Всего заказов: {len(orders)}\n"
        f"✅ Выполнено: {completed_orders}"
    )

    kb = admin_dashboard_keyboard()

    if edit:
        try:
            await target.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await target.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=kb, parse_mode="HTML")


# ==================== АДМИН: АКЦИИ ====================
@dp.message(F.from_user.id == ADMIN_ID, F.text == "🔥 Акции")
@dp.callback_query(F.from_user.id == ADMIN_ID, F.data == "admin_promotions_dashboard")
async def admin_promotions_menu(event):
    if isinstance(event, types.CallbackQuery):
        await event.answer()
        message = event.message
        edit = True
    else:
        message = event
        edit = False

    text = "🔥 <b>Управление акциями</b>\nВыберите действие:"
    kb = admin_promotions_keyboard()

    if edit:
        try:
            await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@dp.callback_query(F.from_user.id == ADMIN_ID, F.data == "admin_create_promotion")
async def admin_start_create_promotion(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    await callback.message.edit_text(
        "🔥 <b>Создание акции</b>\nВведите название акции:",
        parse_mode="HTML",
    )

    await state.set_state(AdminPromotionStates.waiting_for_name)


@dp.message(AdminPromotionStates.waiting_for_name, F.text)
async def admin_promotion_name(message: types.Message, state: FSMContext):
    await state.update_data(promo_name=message.text)
    await message.answer("📝 Введите описание акции:")
    await state.set_state(AdminPromotionStates.waiting_for_description)


@dp.message(AdminPromotionStates.waiting_for_description, F.text)
async def admin_promotion_description(message: types.Message, state: FSMContext):
    await state.update_data(promo_description=message.text)

    await message.answer(
        "📦 Введите список товаров через запятую (точные названия из каталога):\n"
        "Например: <code>🇺🇸 США (+1), 🇺🇦 Украина (+380)</code>",
        parse_mode="HTML",
    )

    await state.set_state(AdminPromotionStates.waiting_for_products)


@dp.message(AdminPromotionStates.waiting_for_products, F.text)
async def admin_promotion_products(message: types.Message, state: FSMContext):
    products = [p.strip() for p in message.text.split(",")]
    await state.update_data(promo_products=products)

    products_text = "\n".join([f"• {p}" for p in products])

    await message.answer(
        f"💰 Введите новые цены для каждого товара (через запятую):\n"
        f"Товары:\n{products_text}\n"
        f"Например: <code>35, 120, 80</code>",
        parse_mode="HTML",
    )

    await state.set_state(AdminPromotionStates.waiting_for_new_prices)


@dp.message(AdminPromotionStates.waiting_for_new_prices, F.text)
async def admin_promotion_prices(message: types.Message, state: FSMContext):
    try:
        prices = [float(p.strip()) for p in message.text.split(",")]
    except ValueError:
        await message.answer("❌ Введите корректные цены через запятую")
        return

    data = await state.get_data()
    products = data.get("promo_products", [])

    if len(prices) != len(products):
        await message.answer(
            f"❌ Количество цен ({len(prices)}) не совпадает с количеством товаров ({len(products)})"
        )
        return

    await state.update_data(promo_prices=prices)

    kb = InlineKeyboardBuilder()

    for hours in [1, 6, 12, 24, 48, 72]:
        kb.button(text=f"{hours} часов", callback_data=f"promo_duration_{hours}")

    kb.adjust(3)

    await message.answer(
        "⏱ Выберите длительность акции:",
        reply_markup=kb.as_markup(),
    )

    await state.set_state(AdminPromotionStates.waiting_for_duration)


@dp.callback_query(
    F.from_user.id == ADMIN_ID,
    AdminPromotionStates.waiting_for_duration,
    F.data.startswith("promo_duration_"),
)
async def admin_promotion_duration(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    hours = int(callback.data.split("_")[-1])
    data = await state.get_data()

    now = datetime.now()
    starts_at = now
    ends_at = now + timedelta(hours=hours)

    promotions = load_promotions()
    promo_id = f"promo_{int(now.timestamp())}"

    new_prices = {}

    for product, price in zip(data.get("promo_products", []), data.get("promo_prices", [])):
        new_prices[product] = price

    promotions[promo_id] = {
        "name": data.get("promo_name"),
        "description": data.get("promo_description"),
        "products": data.get("promo_products", []),
        "new_prices": new_prices,
        "starts_at": starts_at.isoformat(),
        "ends_at": ends_at.isoformat(),
        "is_active": True,
        "created_at": now.isoformat(),
    }

    save_promotions(promotions)

    asyncio.create_task(end_promotion_task(promo_id, hours * 3600))

    text = (
        f"✅ <b>Акция создана!</b>\n"
        f"🔥 Название: {data.get('promo_name')}\n"
        f"⏱ Длительность: {hours} часов\n"
        f"📅 Завершение: {ends_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"Цены обновятся автоматически в каталоге."
    )

    await callback.message.edit_text(text, reply_markup=admin_promotions_keyboard(), parse_mode="HTML")
    await state.clear()


async def end_promotion_task(promo_id: str, delay_seconds: int):
    await asyncio.sleep(delay_seconds)

    promotions = load_promotions()

    if promo_id in promotions:
        promotions[promo_id]["is_active"] = False
        save_promotions(promotions)

        try:
            await bot.send_message(
                ADMIN_ID,
                f"🔥 Акция <b>{promotions[promo_id]['name']}</b> завершена!\n"
                f"Старые цены автоматически восстановлены.",
                parse_mode="HTML",
            )
        except Exception:
            pass


@dp.callback_query(F.from_user.id == ADMIN_ID, F.data.startswith("admin_promo_detail_"))
async def admin_promo_detail(callback: types.CallbackQuery):
    await callback.answer()

    promo_id = callback.data.replace("admin_promo_detail_", "")

    promotions = load_promotions()
    promo = promotions.get(promo_id)

    if not promo:
        await callback.answer("❌ Акция не найдена", show_alert=True)
        return

    status = "🟢 Активна" if promo.get("is_active", True) else "🔴 Завершена"

    text = (
        f"🔥 <b>{promo['name']}</b>\n"
        f"📝 {promo.get('description', 'Без описания')}\n"
        f"<b>Статус:</b> {status}\n"
        f"📅 Начало: {datetime.fromisoformat(promo['starts_at']).strftime('%d.%m.%Y %H:%M')}\n"
        f"📅 Завершение: {datetime.fromisoformat(promo['ends_at']).strftime('%d.%m.%Y %H:%M')}\n"
        f"<b>Товары с акционными ценами:</b>\n"
    )

    for product, price in promo.get("new_prices", {}).items():
        text += f"• {product}: {price} грн\n"

    kb = InlineKeyboardBuilder()

    if promo.get("is_active", True):
        kb.button(text="🛑 Завершить сейчас", callback_data=f"admin_stop_promo_{promo_id}")

    kb.button(text="⬅️ Назад", callback_data="admin_promotions_dashboard")
    kb.adjust(1)

    try:
        await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")


@dp.callback_query(F.from_user.id == ADMIN_ID, F.data.startswith("admin_stop_promo_"))
async def admin_stop_promotion(callback: types.CallbackQuery):
    await callback.answer()

    promo_id = callback.data.replace("admin_stop_promo_", "")

    promotions = load_promotions()

    if promo_id in promotions:
        promotions[promo_id]["is_active"] = False
        save_promotions(promotions)

    await callback.answer("✅ Акция завершена", show_alert=True)
    await admin_promotions_menu(callback)


# ==================== АДМИН: ПРОМОКОДЫ ====================
@dp.message(F.from_user.id == ADMIN_ID, F.text == "🎟 Промокоды")
@dp.callback_query(F.from_user.id == ADMIN_ID, F.data == "admin_promo_dashboard")
async def admin_promo_codes_menu(event):
    if isinstance(event, types.CallbackQuery):
        await event.answer()
        message = event.message
        edit = True
    else:
        message = event
        edit = False

    text = "🎟 <b>Управление промокодами</b>\nВыберите действие:"
    kb = admin_promo_codes_keyboard()

    if edit:
        try:
            await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@dp.callback_query(F.from_user.id == ADMIN_ID, F.data == "admin_create_promo_code")
async def admin_start_create_promo(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text("🎟 Введите код промокода (например, SALE2026):")
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
        f"Код: <code>{code}</code>\nВыберите тип скидки:",
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

    kb = InlineKeyboardBuilder()
    kb.button(text="♾ Без ограничений", callback_data="promo_unlimited")

    for n in [10, 50, 100, 500]:
        kb.button(text=f"{n} использований", callback_data=f"promo_max_{n}")

    kb.adjust(1)

    await message.answer(
        "Максимальное количество использований:",
        reply_markup=kb.as_markup(),
    )

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

    await callback.message.edit_text(
        "Срок действия промокода:",
        reply_markup=kb.as_markup(),
    )

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
    }

    save_promo_codes(promo_codes)

    if data["discount_type"] == "percent":
        discount_desc = f"{data['discount_value']}%"
    else:
        discount_desc = f"{data['discount_value']} грн"

    text = (
        f"✅ <b>Промокод создан!</b>\n"
        f"🎟 Код: <code>{data['promo_code']}</code>\n"
        f"💰 Скидка: {discount_desc}\n"
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

    status = "🟢 Активен" if promo.get("is_active", True) else "🔴 Неактивен"

    if promo["discount_type"] == "percent":
        discount_desc = f"{promo['discount_value']}%"
    else:
        discount_desc = f"{promo['discount_value']} грн"

    uses_text = f"{promo.get('current_uses', 0)}/{promo.get('max_uses') or '♾'}"

    text = (
        f"🎟 <b>Промокод {code}</b>\n"
        f"💰 Скидка: {discount_desc}\n"
        f"<b>Статус:</b> {status}\n"
        f"🔢 Использований: {uses_text}\n"
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


@dp.callback_query(F.from_user.id == ADMIN_ID, F.data.startswith("admin_deactivate_promo_"))
async def admin_deactivate_promo(callback: types.CallbackQuery):
    await callback.answer()

    code = callback.data.replace("admin_deactivate_promo_", "")

    promo_codes = load_promo_codes()

    if code in promo_codes:
        promo_codes[code]["is_active"] = False
        save_promo_codes(promo_codes)

    await callback.answer("✅ Деактивировано", show_alert=True)


@dp.callback_query(F.from_user.id == ADMIN_ID, F.data.startswith("admin_activate_promo_"))
async def admin_activate_promo(callback: types.CallbackQuery):
    await callback.answer()

    code = callback.data.replace("admin_activate_promo_", "")

    promo_codes = load_promo_codes()

    if code in promo_codes:
        promo_codes[code]["is_active"] = True
        save_promo_codes(promo_codes)

    await callback.answer("✅ Активировано", show_alert=True)


@dp.callback_query(F.from_user.id == ADMIN_ID, F.data.startswith("admin_delete_promo_"))
async def admin_delete_promo(callback: types.CallbackQuery):
    await callback.answer()

    code = callback.data.replace("admin_delete_promo_", "")

    promo_codes = load_promo_codes()

    if code in promo_codes:
        del promo_codes[code]
        save_promo_codes(promo_codes)

    await callback.answer("🗑 Удалено", show_alert=True)


# ==================== АДМИН: УРОВНИ ====================
@dp.message(F.from_user.id == ADMIN_ID, F.text == "⭐ Уровни")
@dp.callback_query(F.from_user.id == ADMIN_ID, F.data == "admin_levels_dashboard")
async def admin_levels_menu(event):
    if isinstance(event, types.CallbackQuery):
        await event.answer()
        message = event.message
        edit = True
    else:
        message = event
        edit = False

    levels_config = {
        "Бронза": ("🥉", get_setting("level_bronze_min", 0), get_setting("level_bronze_discount", 0)),
        "Серебро": ("🥈", get_setting("level_silver_min", 500), get_setting("level_silver_discount", 3)),
        "Золото": ("🥇", get_setting("level_gold_min", 1500), get_setting("level_gold_discount", 5)),
        "Платина": ("💎", get_setting("level_platinum_min", 3000), get_setting("level_platinum_discount", 7)),
        "VIP": ("👑", get_setting("level_vip_min", 5000), get_setting("level_vip_discount", 10)),
    }

    text = "⭐ <b>Уровни клиентов</b>\n"

    for name, (emoji, min_spent, discount) in levels_config.items():
        text += f"{emoji} <b>{name}</b>\n"
        text += f"   Порог: {min_spent} грн\n"
        text += f"   Скидка: {discount}%\n"

    kb = admin_levels_keyboard()

    if edit:
        try:
            await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@dp.callback_query(F.from_user.id == ADMIN_ID, F.data.startswith("admin_edit_level_"))
async def admin_edit_level_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    level_key = callback.data.replace("admin_edit_level_", "")
    level_name = LEVEL_KEYS.get(level_key, level_key)

    await state.update_data(edit_level=level_key)

    kb = InlineKeyboardBuilder()
    kb.button(text="💵 Изменить порог", callback_data="edit_level_min")
    kb.button(text="🎁 Изменить скидку", callback_data="edit_level_discount")
    kb.button(text="⬅️ Назад", callback_data="admin_levels_dashboard")
    kb.adjust(1)

    await callback.message.edit_text(
        f"Редактирование уровня <b>{level_name}</b>\nВыберите что изменить:",
        reply_markup=kb.as_markup(),
        parse_mode="HTML",
    )


@dp.callback_query(F.from_user.id == ADMIN_ID, F.data == "edit_level_min")
async def admin_edit_level_min_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    await state.update_data(edit_field="min_spent")
    await callback.message.edit_text("Введите новый порог (сумма в грн):")

    await state.set_state(AdminLevelStates.waiting_for_min_spent)


@dp.callback_query(F.from_user.id == ADMIN_ID, F.data == "edit_level_discount")
async def admin_edit_level_discount_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    await state.update_data(edit_field="discount")
    await callback.message.edit_text("Введите новую скидку (в процентах):")

    await state.set_state(AdminLevelStates.waiting_for_discount)


@dp.message(AdminLevelStates.waiting_for_min_spent, F.text)
async def admin_save_level_min(message: types.Message, state: FSMContext):
    try:
        value = float(message.text)
    except ValueError:
        await message.answer("❌ Введите корректное число")
        return

    data = await state.get_data()
    level_key = data.get("edit_level", "bronze")
    level_name = LEVEL_KEYS.get(level_key, level_key)

    settings = load_settings()
    key = f"level_{level_key}_min"
    settings[key] = value
    save_settings(settings)

    await message.answer(
        f"✅ Порог для уровня {level_name} установлен: {value} грн",
        reply_markup=get_admin_reply_keyboard(),
    )

    await state.clear()


@dp.message(AdminLevelStates.waiting_for_discount, F.text)
async def admin_save_level_discount(message: types.Message, state: FSMContext):
    try:
        value = float(message.text)

        if value < 0 or value > 100:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите число от 0 до 100")
        return

    data = await state.get_data()
    level_key = data.get("edit_level", "bronze")
    level_name = LEVEL_KEYS.get(level_key, level_key)

    settings = load_settings()
    key = f"level_{level_key}_discount"
    settings[key] = value
    save_settings(settings)

    await message.answer(
        f"✅ Скидка для уровня {level_name} установлена: {value}%",
        reply_markup=get_admin_reply_keyboard(),
    )

    await state.clear()


# ==================== АДМИН: АВТОРАССЫЛКИ ====================
@dp.message(F.from_user.id == ADMIN_ID, F.text == "📢 Рассылки")
@dp.callback_query(F.from_user.id == ADMIN_ID, F.data == "admin_broadcasts_dashboard")
async def admin_auto_broadcasts_menu(event):
    if isinstance(event, types.CallbackQuery):
        await event.answer()
        message = event.message
        edit = True
    else:
        message = event
        edit = False

    broadcasts = load_broadcasts()

    text = "📢 <b>Автоматические рассылки</b>\n"
    text += "Напоминания пользователям, которые не покупали:\n"

    if broadcasts:
        for bc_id, bc in broadcasts.items():
            status = "🟢" if bc.get("is_active", True) else "🔴"
            text += f"{status} <b>{bc['days_inactive']} дней</b>\n"
            text += f"   {bc.get('message_text', '')[:50]}...\n"
    else:
        text += "<i>Нет настроенных рассылок</i>\n"

    kb = admin_broadcasts_keyboard()

    if edit:
        try:
            await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@dp.callback_query(F.from_user.id == ADMIN_ID, F.data == "admin_create_broadcast_template")
async def admin_start_create_broadcast(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    kb = InlineKeyboardBuilder()

    for days in [3, 7, 14, 30]:
        kb.button(text=f"{days} дней", callback_data=f"broadcast_days_{days}")

    kb.adjust(2)

    await callback.message.edit_text(
        "📢 Через сколько дней неактивности отправлять напоминание?",
        reply_markup=kb.as_markup(),
    )

    await state.set_state(AdminBroadcastTemplateStates.waiting_for_days)


@dp.callback_query(
    F.from_user.id == ADMIN_ID,
    AdminBroadcastTemplateStates.waiting_for_days,
    F.data.startswith("broadcast_days_"),
)
async def admin_broadcast_days(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    days = int(callback.data.split("_")[-1])
    await state.update_data(broadcast_days=days)

    await callback.message.edit_text(
        f"📝 Введите текст сообщения для напоминания через {days} дней (поддерживается HTML):"
    )

    await state.set_state(AdminBroadcastTemplateStates.waiting_for_text)


@dp.message(AdminBroadcastTemplateStates.waiting_for_text, F.text)
async def admin_broadcast_text(message: types.Message, state: FSMContext):
    await state.update_data(broadcast_text=message.text)

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Без кнопки", callback_data="broadcast_no_button")
    kb.button(text="➕ Добавить кнопку", callback_data="broadcast_add_button")
    kb.adjust(1)

    await message.answer(
        "Добавить кнопку под сообщением?",
        reply_markup=kb.as_markup(),
    )

    await state.set_state(AdminBroadcastTemplateStates.waiting_for_button)


@dp.callback_query(
    F.from_user.id == ADMIN_ID,
    AdminBroadcastTemplateStates.waiting_for_button,
    F.data.startswith("broadcast_"),
)
async def admin_broadcast_button(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    data = await state.get_data()

    if callback.data == "broadcast_no_button":
        broadcasts = load_broadcasts()
        bc_id = f"bc_{data['broadcast_days']}"

        broadcasts[bc_id] = {
            "days_inactive": data["broadcast_days"],
            "message_text": data["broadcast_text"],
            "button_text": None,
            "button_url": None,
            "is_active": True,
            "created_at": datetime.now().isoformat(),
        }

        save_broadcasts(broadcasts)

        await callback.message.edit_text(
            f"✅ Рассылка через {data['broadcast_days']} дней настроена!",
            reply_markup=admin_broadcasts_keyboard(),
        )

        await state.clear()
    else:
        await callback.message.edit_text(
            "Введите текст кнопки и URL через запятую:\n"
            "Например: <code>🛍 В каталог, https://t.me/bot?start=catalog</code>",
            parse_mode="HTML",
        )


@dp.message(AdminBroadcastTemplateStates.waiting_for_button, F.text)
async def admin_broadcast_button_input(message: types.Message, state: FSMContext):
    try:
        parts = message.text.split(",", 1)

        if len(parts) != 2:
            await message.answer("❌ Введите в формате: текст, URL")
            return

        button_text = parts[0].strip()
        button_url = parts[1].strip()
    except Exception:
        await message.answer("❌ Неправильный формат")
        return

    data = await state.get_data()

    broadcasts = load_broadcasts()
    bc_id = f"bc_{data['broadcast_days']}"

    broadcasts[bc_id] = {
        "days_inactive": data["broadcast_days"],
        "message_text": data["broadcast_text"],
        "button_text": button_text,
        "button_url": button_url,
        "is_active": True,
        "created_at": datetime.now().isoformat(),
    }

    save_broadcasts(broadcasts)

    await message.answer(
        f"✅ Рассылка через {data['broadcast_days']} дней настроена!",
        reply_markup=admin_broadcasts_keyboard(),
    )

    await state.clear()


@dp.callback_query(F.from_user.id == ADMIN_ID, F.data.startswith("admin_broadcast_detail_"))
async def admin_broadcast_detail(callback: types.CallbackQuery):
    await callback.answer()

    bc_id = callback.data.replace("admin_broadcast_detail_", "")

    broadcasts = load_broadcasts()
    bc = broadcasts.get(bc_id)

    if not bc:
        await callback.answer("❌ Не найдено", show_alert=True)
        return

    status = "🟢 Активна" if bc.get("is_active", True) else "🔴 Неактивна"

    text = (
        f"📢 <b>Рассылка через {bc['days_inactive']} дней</b>\n"
        f"<b>Статус:</b> {status}\n"
        f"<b>Текст:</b>\n{bc.get('message_text', '')}\n"
    )

    if bc.get("button_text") and bc.get("button_url"):
        text += f"<b>Кнопка:</b> {bc['button_text']} → {bc['button_url']}\n"

    kb = InlineKeyboardBuilder()

    if bc.get("is_active", True):
        kb.button(text="🛑 Выключить", callback_data=f"admin_disable_bc_{bc_id}")
    else:
        kb.button(text="✅ Включить", callback_data=f"admin_enable_bc_{bc_id}")

    kb.button(text="🗑 Удалить", callback_data=f"admin_delete_bc_{bc_id}")
    kb.button(text="⬅️ Назад", callback_data="admin_broadcasts_dashboard")
    kb.adjust(1)

    try:
        await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")


@dp.callback_query(F.from_user.id == ADMIN_ID, F.data.startswith("admin_disable_bc_"))
async def admin_disable_bc(callback: types.CallbackQuery):
    await callback.answer()

    bc_id = callback.data.replace("admin_disable_bc_", "")

    broadcasts = load_broadcasts()

    if bc_id in broadcasts:
        broadcasts[bc_id]["is_active"] = False
        save_broadcasts(broadcasts)

    await callback.answer("✅ Выключено", show_alert=True)


@dp.callback_query(F.from_user.id == ADMIN_ID, F.data.startswith("admin_enable_bc_"))
async def admin_enable_bc(callback: types.CallbackQuery):
    await callback.answer()

    bc_id = callback.data.replace("admin_enable_bc_", "")

    broadcasts = load_broadcasts()

    if bc_id in broadcasts:
        broadcasts[bc_id]["is_active"] = True
        save_broadcasts(broadcasts)

    await callback.answer("✅ Включено", show_alert=True)


@dp.callback_query(F.from_user.id == ADMIN_ID, F.data.startswith("admin_delete_bc_"))
async def admin_delete_bc(callback: types.CallbackQuery):
    await callback.answer()

    bc_id = callback.data.replace("admin_delete_bc_", "")

    broadcasts = load_broadcasts()

    if bc_id in broadcasts:
        del broadcasts[bc_id]
        save_broadcasts(broadcasts)

    await callback.answer("🗑 Удалено", show_alert=True)


# ==================== АДМИН: РЕФЕРАЛЫ ====================
@dp.message(F.from_user.id == ADMIN_ID, F.text == "👥 Рефералы")
@dp.callback_query(F.from_user.id == ADMIN_ID, F.data == "admin_referrals_dashboard")
async def admin_referrals_menu(event):
    if isinstance(event, types.CallbackQuery):
        await event.answer()
        message = event.message
        edit = True
    else:
        message = event
        edit = False

    referrals = load_referrals()

    bonus_percent = get_setting("referral_bonus_percent", 5.0)
    total_referrals = sum(len(r.get("referrals_list", [])) for r in referrals.values())
    total_earned = sum(r.get("total_earned", 0) for r in referrals.values())

    top_referrers = sorted(
        [(uid, r) for uid, r in referrals.items() if r.get("referrals_list")],
        key=lambda x: len(x[1].get("referrals_list", [])),
        reverse=True,
    )[:5]

    text = (
        f"👥 <b>Реферальная система</b>\n"
        f"💰 <b>Текущий бонус:</b> {bonus_percent}%\n"
        f"👥 Всего рефералов: {total_referrals}\n"
        f"💸 Сумма бонусов: {total_earned:.2f} грн\n"
    )

    if top_referrers:
        text += "<b>🏆 ТОП-рефереры:</b>\n"

        for i, (uid, r) in enumerate(top_referrers, 1):
            users_data = load_users()
            user = users_data.get(str(uid), {})

            username = user.get("username", "неизвестно")
            refs_count = len(r.get("referrals_list", []))
            earned = r.get("total_earned", 0)

            text += f"{i}. @{username} — {refs_count} реф., {earned:.2f} грн\n"

    kb = admin_referrals_settings_keyboard()

    if edit:
        try:
            await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@dp.callback_query(F.from_user.id == ADMIN_ID, F.data == "admin_edit_referral_bonus")
async def admin_edit_referral_bonus_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    current = get_setting("referral_bonus_percent", 5.0)

    await callback.message.edit_text(
        f"Текущий бонус: {current}%\nВведите новый процент бонуса:"
    )

    await state.set_state(AdminReferralSettingsStates.waiting_for_bonus_percent)


@dp.message(AdminReferralSettingsStates.waiting_for_bonus_percent, F.text)
async def admin_save_referral_bonus(message: types.Message, state: FSMContext):
    try:
        value = float(message.text)

        if value < 0 or value > 100:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите число от 0 до 100")
        return

    settings = load_settings()
    settings["referral_bonus_percent"] = value
    save_settings(settings)

    await message.answer(
        f"✅ Реферальный бонус установлен: {value}%",
        reply_markup=get_admin_reply_keyboard(),
    )

    await state.clear()


# ==================== АДМИН: АНАЛИТИКА ====================
@dp.message(F.from_user.id == ADMIN_ID, F.text == "📊 Аналитика")
@dp.callback_query(F.from_user.id == ADMIN_ID, F.data == "admin_analytics_dashboard")
async def admin_analytics_menu(event):
    if isinstance(event, types.CallbackQuery):
        await event.answer()
        message = event.message
        edit = True
    else:
        message = event
        edit = False

    text = "📊 <b>Аналитика</b>\nВыберите тип аналитики:"
    kb = admin_analytics_keyboard()

    if edit:
        try:
            await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@dp.callback_query(F.from_user.id == ADMIN_ID, F.data == "admin_analytics_by_days")
async def admin_analytics_by_days(callback: types.CallbackQuery):
    await callback.answer()

    orders = load_orders()
    now = datetime.now()

    days_data = {}

    for i in range(30):
        day = now - timedelta(days=i)
        day_key = day.strftime("%d.%m")
        days_data[day_key] = {"revenue": 0, "orders": 0}

    for order in orders.values():
        if order["status"] == "completed" and order.get("completed_at"):
            try:
                dt = datetime.fromisoformat(order["completed_at"])

                if (now - dt).days < 30:
                    day_key = dt.strftime("%d.%m")

                    if day_key in days_data:
                        if not isinstance(order.get("total", 0), str):
                            days_data[day_key]["revenue"] += order.get("total", 0)

                        days_data[day_key]["orders"] += 1
            except Exception:
                pass

    text = "📊 <b>Прибыль по дням (30 дней)</b>\n"

    for day_key in reversed(list(days_data.keys())):
        data = days_data[day_key]

        if data["revenue"] > 0 or data["orders"] > 0:
            text += f"📅 {day_key}: {data['revenue']:.2f} грн ({data['orders']} зак.)\n"

    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="admin_analytics_dashboard")

    try:
        await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")


@dp.callback_query(F.from_user.id == ADMIN_ID, F.data == "admin_analytics_by_hours")
async def admin_analytics_by_hours(callback: types.CallbackQuery):
    await callback.answer()

    orders = load_orders()
    hours_data = {h: {"revenue": 0, "orders": 0} for h in range(24)}

    for order in orders.values():
        if order["status"] == "completed" and order.get("completed_at"):
            try:
                dt = datetime.fromisoformat(order["completed_at"])
                hour = dt.hour

                if not isinstance(order.get("total", 0), str):
                    hours_data[hour]["revenue"] += order.get("total", 0)

                hours_data[hour]["orders"] += 1
            except Exception:
                pass

    text = "⏰ <b>Продажи по часам</b>\n"

    for h in range(24):
        data = hours_data[h]

        if data["orders"] > 0:
            text += f"{h:02d}:00 - {h:02d}:59 : {data['revenue']:.2f} грн ({data['orders']} зак.)\n"

    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="admin_analytics_dashboard")

    try:
        await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")


@dp.callback_query(F.from_user.id == ADMIN_ID, F.data == "admin_analytics_by_country")
async def admin_analytics_by_country(callback: types.CallbackQuery):
    await callback.answer()

    orders = load_orders()
    country_stats = {}

    for order in orders.values():
        if order["status"] == "completed":
            product = order["product"]
            country = "Неизвестно"

            for emoji in [
                "🇲🇲", "🇺🇸", "🇨🇴", "🇧🇩", "🇫🇷", "🇧🇷", "🇺🇿", "🇹🇭",
                "🇬🇧", "🇺🇦", "🇧🇾", "🇰🇿", "🇵🇱", "🇷🇺", "🇩🇪",
                "🇨🇦", "🇭🇺", "🇬🇱",
            ]:
                if product.startswith(emoji):
                    parts = product.split()

                    if len(parts) > 1:
                        country = parts[1]

                    break

            if country not in country_stats:
                country_stats[country] = {"revenue": 0, "orders": 0}

            if not isinstance(order.get("total", 0), str):
                country_stats[country]["revenue"] += order.get("total", 0)

            country_stats[country]["orders"] += 1

    text = "🌍 <b>Продажи по странам</b>\n"

    sorted_countries = sorted(country_stats.items(), key=lambda x: x[1]["revenue"], reverse=True)

    for country, data in sorted_countries:
        text += f"• {country}: {data['revenue']:.2f} грн ({data['orders']} зак.)\n"

    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="admin_analytics_dashboard")

    try:
        await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")


# ==================== АДМИН: ИСТОЧНИКИ ТРАФИКА ====================
@dp.message(F.from_user.id == ADMIN_ID, F.text == "🔗 Источники")
@dp.callback_query(F.from_user.id == ADMIN_ID, F.data == "admin_traffic_dashboard")
async def admin_traffic_sources_menu(event):
    if isinstance(event, types.CallbackQuery):
        await event.answer()
        message = event.message
        edit = True
    else:
        message = event
        edit = False

    sources = load_traffic_sources()

    text = "🔗 <b>Источники трафика</b>\n"

    if not sources:
        text += "<i>Данные отсутствуют. Используйте deep links:\n"
        text += "<code>/start reddit</code>\n"
        text += "<code>/start tiktok</code>\n"
        text += "<code>/start youtube</code></i>\n"
    else:
        sorted_sources = sorted(sources.items(), key=lambda x: x[1].get("total_revenue", 0), reverse=True)

        for name, data in sorted_sources:
            visits = data.get("total_visits", 0)
            regs = data.get("total_registrations", 0)
            purchases = data.get("total_purchases", 0)
            revenue = data.get("total_revenue", 0)
            conversion = (purchases / visits * 100) if visits > 0 else 0

            text += f"<b>📍 {name}</b>\n"
            text += f"• 📥 Переходов: {visits}\n"
            text += f"• 👤 Регистраций: {regs}\n"
            text += f"• 🛒 Покупок: {purchases}\n"
            text += f"• 💰 Доход: {revenue:.2f} грн\n"
            text += f"• 📈 Конверсия: {conversion:.2f}%\n"

            if purchases > 0:
                text += f"• 💵 Средний чек: {(revenue / purchases):.2f} грн\n"

    kb = admin_traffic_keyboard()

    if edit:
        try:
            await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


# ==================== АДМИН: ПОИСК ЗАКАЗОВ ====================
@dp.callback_query(F.from_user.id == ADMIN_ID, F.data == "admin_search_orders")
async def admin_start_search(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    await callback.message.edit_text(
        "🔍 <b>Поиск заказов</b>\n"
        "Введите:\n"
        "• Номер заказа (#000001)\n"
        "• Telegram ID\n"
        "• Имя пользователя\n"
        "• Номер телефона\n"
        "• Название товара"
    )

    await state.set_state(AdminSearchStates.waiting_for_query)


@dp.message(AdminSearchStates.waiting_for_query, F.text)
async def admin_process_search(message: types.Message, state: FSMContext):
    query = message.text.strip()

    orders = load_orders()
    results = []

    for key, order in orders.items():
        if query in order.get("short_id", ""):
            results.append((key, order))
            continue

        if query.isdigit() and order["user_id"] == int(query):
            results.append((key, order))
            continue

        if query.lower() in order.get("username", "").lower():
            results.append((key, order))
            continue

        if query in (order.get("phone") or ""):
            results.append((key, order))
            continue

        if query.lower() in order.get("product", "").lower():
            results.append((key, order))
            continue

    if not results:
        await message.answer("❌ Ничего не найдено", reply_markup=get_admin_reply_keyboard())
        await state.clear()
        return

    text = f"🔍 <b>Найдено {len(results)} заказов:</b>\n"

    kb = InlineKeyboardBuilder()

    for key, order in results[:10]:
        emoji, status_text = STATUS_CONFIG.get(order["status"], ("❓", "Неизвестно"))
        symbol = method_symbol(order.get("payment_method", "uah"))
        short_id = order.get("short_id", key[:8])

        text += f"{emoji} {short_id} | {order['product'][:20]} | {order['total']} {symbol}\n"

        kb.button(text=f"📋 {short_id}", callback_data=f"admin_order_detail_{key}")

    kb.button(text="⬅️ Назад", callback_data="admin_dashboard_refresh")
    kb.adjust(1)

    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    await state.clear()


# ==================== АДМИН: ЧАТ С ПОКУПАТЕЛЕМ ====================
@dp.callback_query(F.from_user.id == ADMIN_ID, F.data.startswith("admin_chat_with_user_"))
async def admin_start_chat_with_user(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    order_id = callback.data.replace("admin_chat_with_user_", "")

    orders = load_orders()
    real_key = find_order_key(orders, order_id)

    if not real_key:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    order = orders[real_key]
    order_id = real_key

    chat_history = load_chat_history()
    history = chat_history.get(order_id, [])

    text = f"💬 Чат по заказу {order.get('short_id', '')}\n"
    text += f"👤 @{order.get('username', 'неизвестно')}\n"

    if history:
        for msg in history[-10:]:
            sender = "👤 Покупатель" if msg["sender"] == "user" else "👨‍💼 Админ"
            date = datetime.fromisoformat(msg["date"]).strftime("%H:%M %d.%m")
            text += f"{sender} ({date}):\n{msg['text']}\n"
    else:
        text += "<i>История пуста</i>\n"

    text += "Введите сообщение для отправки покупателю:"

    await state.update_data(admin_chat_order_id=order_id)
    await state.set_state(AdminChatStates.waiting_for_message)

    try:
        await callback.message.edit_text(text, parse_mode=None)
    except Exception:
        await callback.message.answer(text, parse_mode=None)


@dp.message(AdminChatStates.waiting_for_message, F.text)
async def admin_send_chat_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("admin_chat_order_id")

    orders = load_orders()
    real_key = find_order_key(orders, order_id)

    if not real_key:
        await message.answer("❌ Заказ не найден")
        await state.clear()
        return

    order = orders[real_key]

    try:
        await bot.send_message(
            chat_id=order["user_id"],
            text=f"💬 Сообщение от администратора по заказу {order.get('short_id', '')}:\n{message.text}",
            parse_mode=None,
        )

        chat_history = load_chat_history()

        if real_key not in chat_history:
            chat_history[real_key] = []

        chat_history[real_key].append({
            "sender": "admin",
            "text": message.text,
            "date": datetime.now().isoformat(),
        })

        save_chat_history(chat_history)

        await message.answer("✅ Сообщение отправлено покупателю", reply_markup=get_admin_reply_keyboard())
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}", reply_markup=get_admin_reply_keyboard())

    await state.clear()


# ==================== ФОНОВЫЕ ЗАДАЧИ ====================
async def auto_broadcast_scheduler():
    while True:
        try:
            broadcasts = load_broadcasts()
            users = load_users()
            orders = load_orders()

            now = datetime.now()

            for bc_id, bc in broadcasts.items():
                if not bc.get("is_active", True):
                    continue

                days_inactive = bc.get("days_inactive")

                if not days_inactive:
                    continue

                for user_id_str, user_data in users.items():
                    user_id = int(user_id_str)

                    user_orders = [
                        o for o in orders.values()
                        if o["user_id"] == user_id and o["status"] == "completed"
                    ]

                    if not user_orders:
                        continue

                    last_order = max(
                        user_orders,
                        key=lambda x: x.get("completed_at", x.get("created_at", "")),
                    )

                    try:
                        last_date = datetime.fromisoformat(
                            last_order.get("completed_at", last_order["created_at"])
                        )
                    except Exception:
                        continue

                    days_since = (now - last_date).days

                    if days_since == days_inactive:
                        sent_key = f"sent_bc_{bc_id}"

                        if user_data.get(sent_key):
                            continue

                        try:
                            kb = None

                            if bc.get("button_text") and bc.get("button_url"):
                                kb = InlineKeyboardBuilder()
                                kb.button(text=bc["button_text"], url=bc["button_url"])
                                kb = kb.as_markup()

                            await bot.send_message(
                                chat_id=user_id,
                                text=bc["message_text"],
                                reply_markup=kb,
                                parse_mode="HTML",
                            )

                            users[user_id_str][sent_key] = datetime.now().isoformat()
                            save_users(users)

                            await asyncio.sleep(0.1)
                        except Exception as e:
                            logger.error(f"Failed auto broadcast to {user_id}: {e}")

        except Exception as e:
            logger.error(f"Broadcast scheduler error: {e}")

        await asyncio.sleep(3600)


# ==================== ЗАПУСК ====================
async def main():
    print("=" * 50)
    print("OverPass Store Bot")
    print("Баланс удалён, реферальные бонусы выдаются промокодами")
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
