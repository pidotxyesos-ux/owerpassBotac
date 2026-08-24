import asyncio
import json
import logging
import re
import random
import aiohttp
from typing import Dict, List, Optional
from ddgs import DDGS
from openai import AsyncOpenAI
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# =====================================================================
# CONFIGURATION
# =====================================================================
OPENAI_API_KEY = "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"
TELEGRAM_BOT_TOKEN = "8628836250:AAFu3eHYTLa9hYtwBBiUemVkPmF_vEDrXos"
ADMIN_CHAT_ID = 8984958620  # Ваш особистий Telegram ID

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

is_scanning = False
scan_task = None

# Список дозволених ID та Username користувачів (Адмін за замовчуванням)
ALLOWED_USERS = set([ADMIN_CHAT_ID])
USERNAMES_MAP = {}  # Зберігає мапінг @username -> user_id

# Стан фільтрів пошуку
user_filters = {
    "categories": [],
    "cities": [],
    "min_price": 0
}

# =====================================================================
# НІШІ ТА КАТЕГОРІЇ
# =====================================================================
CATEGORIES = {
    "construction": "🏗 Будівництво та ремонт",
    "auto": "🚗 Авто та логістика",
    "b2b": "⚖️ Юриспруденція та B2B",
    "services": "📦 Оренда та послуги",
    "med": "🏥 Медицина та спец-послуги"
}

ALL_NICHES = [
    {"name": "будівництво ангарів та складів", "cat": "construction", "product": "site_calc"},
    {"name": "монтаж сонячних електростанцій", "cat": "construction", "product": "site_calc"},
    {"name": "буріння свердловин на воду", "cat": "construction", "product": "site_calc"},
    {"name": "монтаж септиків та автономної каналізації", "cat": "construction", "product": "landing_page"},
    {"name": "утеплення фасадів та пінополіуретан", "cat": "construction", "product": "site_calc"},
    {"name": "будівництво басейнів та купелей", "cat": "construction", "product": "portfolio_site"},
    {"name": "монтаж автополиву та ландшафт", "cat": "construction", "product": "site_calc"},
    {"name": "промислова епоксидна підлога", "cat": "construction", "product": "b2b_landing"},
    {"name": "монтаж опалення та теплових насосів", "cat": "construction", "product": "site_calc"},
    {"name": "дизайн інтер'єру преміум", "cat": "construction", "product": "portfolio_site"},

    {"name": "послуги евакуатора цілодобово", "cat": "auto", "product": "fast_landing_bot"},
    {"name": "вантажоперевезення та квартирні переїзди", "cat": "auto", "product": "bot_calc"},
    {"name": "детейлінг та обклеювання авто плівкою", "cat": "auto", "product": "site_calc"},
    {"name": "автопідбір під ключ", "cat": "auto", "product": "bot_quiz"},
    {"name": "приганяння авто з США та Європи", "cat": "auto", "product": "site_calc"},
    {"name": "викуп авто після ДТП", "cat": "auto", "product": "fast_bot_estimate"},
    {"name": "ремонт АКПП та варіаторів", "cat": "auto", "product": "landing_page"},
    {"name": "оренда спецтехніки екскаватор кран", "cat": "auto", "product": "bot_catalog"},

    {"name": "військовий адвокат консультація", "cat": "b2b", "product": "quiz_bot"},
    {"name": "адвокат з ДТП та позбавлення прав", "cat": "b2b", "product": "quiz_bot"},
    {"name": "банкрутство фізичних осіб", "cat": "b2b", "product": "landing_calc"},
    {"name": "бухгалтерський аутсорсинг FOP ТОВ", "cat": "b2b", "product": "site_calc"},
    {"name": "митно брокерські послуги", "cat": "b2b", "product": "b2b_landing"},
    {"name": "допомога в отриманні грантів бізнесу", "cat": "b2b", "product": "quiz_bot"},
    {"name": "впровадження CRM систем BAS", "cat": "b2b", "product": "b2b_landing"},

    {"name": "прокат будівельного інструменту", "cat": "services", "product": "bot_catalog"},
    {"name": "подобова оренда квартир апартаменти", "cat": "services", "product": "booking_bot"},
    {"name": "оренда авто без водія", "cat": "services", "product": "bot_catalog"},
    {"name": "хімчистка меблів та килимів з виїздом", "cat": "services", "product": "photo_estimate_bot"},
    {"name": "дезинфекція дератизація знищення клопів", "cat": "services", "product": "landing_page"},
    {"name": "вивіз будівельного сміття хлам", "cat": "services", "product": "bot_calc"},
    {"name": "монтаж та обслуговування відеонагляду", "cat": "services", "product": "site_calc"},

    {"name": "наркологічна клініка виклики 24/7", "cat": "med", "product": "anonymous_bot"},
    {"name": "реабілітаційний центр залежності", "cat": "med", "product": "landing_page"},
    {"name": "стоматологічна імплантація вініри", "cat": "med", "product": "booking_bot"},
    {"name": "центр МРТ та КТ діагностики", "cat": "med", "product": "booking_bot"},
    {"name": "служба ритуальних послуг 24/7", "cat": "med", "product": "fast_landing_bot"}
]

ALL_CITIES = [
    "Київ", "Львів", "Одеса", "Дніпро", "Харків",
    "Вінниця", "Івано-Франківськ", "Тернопіль", "Чернівці",
    "Запоріжжя", "Полтава", "Черкаси", "Житомир", "Хмельницький",
    "Рівне", "Луцьк", "Ужгород", "Миколаїв"
]

control_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚀 Запустити Mass Scan"), KeyboardButton(text="⏹ Зупинити")],
        [KeyboardButton(text="⚙️ Налаштувати фільтри"), KeyboardButton(text="👥 Менеджери")]
    ],
    resize_keyboard=True
)


# =====================================================================
# HUNTER CLASS
# =====================================================================
class SmartLeadHunter:
    def __init__(self):
        self.session = None

    async def init_session(self):
        if not self.session or self.session.closed:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "uk-UA,uk;q=0.9,en;q=0.8",
            }
            self.session = aiohttp.ClientSession(headers=headers)

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def fast_search(self, query: str, max_results: int = 3) -> List[str]:
        def _search():
            logging.getLogger("ddgs").setLevel(logging.ERROR)
            logging.getLogger("duckduckgo_search").setLevel(logging.ERROR)
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, region='uk-ua', safesearch='off', max_results=max_results,
                                             backend='duckduckgo'))
                    return [r['href'] for r in results if isinstance(r, dict) and 'href' in r]
            except Exception:
                try:
                    with DDGS() as ddgs:
                        results = list(ddgs.text(query, region='uk-ua', max_results=max_results, backend='html'))
                        return [r['href'] for r in results if isinstance(r, dict) and 'href' in r]
                except Exception as inner_e:
                    logging.error(f"Search failed: {inner_e}")
                    return []

        return await asyncio.to_thread(_search)

    async def find_contacts_deep(self, name: str, city: str) -> Dict:
        contacts = {"phone": [], "email": [], "socials": {}, "website": None}
        queries = [f"{name} {city} телефон instagram", f"{name} {city} офіційний сайт"]
        found_urls = set()

        for query in queries:
            results = await self.fast_search(query, max_results=3)
            for url in results:
                if url in found_urls:
                    continue
                found_urls.add(url)
                url_lower = url.lower()

                if "instagram.com" in url_lower:
                    contacts["socials"]["instagram"] = url
                elif "tiktok.com" in url_lower:
                    contacts["socials"]["tiktok"] = url
                elif "facebook.com" in url_lower:
                    contacts["socials"]["facebook"] = url
                elif "t.me/" in url_lower or "telegram.me" in url_lower:
                    contacts["socials"]["telegram"] = url
                elif not any(x in url_lower for x in ["instagram", "facebook", "t.me", "youtube", "tiktok", "twitter"]):
                    if not contacts["website"]:
                        contacts["website"] = url

            if contacts["website"]:
                page_content = await self.fetch_page_content(contacts["website"])
                if page_content:
                    contacts["phone"].extend(self.extract_phones(page_content))
                    contacts["email"].extend(self.extract_emails(page_content))

        contacts["phone"] = list(set(contacts["phone"]))
        contacts["email"] = list(set(contacts["email"]))
        return contacts

    async def fetch_page_content(self, url: str) -> Optional[str]:
        try:
            async with self.session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    return await resp.text()
        except Exception:
            return None
        return None

    def extract_phones(self, text: str) -> List[str]:
        patterns = [r'\+?380\d{9}', r'0\d{9}']
        phones = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                clean_num = re.sub(r'\D', '', match)
                if len(clean_num) == 12 and clean_num.startswith('380'):
                    phones.append(f"+{clean_num}")
                elif len(clean_num) == 10 and clean_num.startswith('0'):
                    phones.append(f"+38{clean_num}")
        return phones[:3]

    def extract_emails(self, text: str) -> List[str]:
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        return re.findall(pattern, text)[:3]

    async def analyze_with_gpt(self, business_data: Dict, contacts: Dict) -> Dict:
        has_website = bool(contacts.get("website"))
        has_socials = bool(contacts.get("socials"))

        prompt = f"""
        Ти - досвідчений менеджер з продажів IT-послуг (боти, сайти, автоматизація).
        Проаналізуй клієнта і напиши ПОВНЕ готове холодне повідомлення у месенджер (Telegram/Instagram/Viber).

        Клієнт:
        - Назва/Ніша: {business_data['name']} ({business_data['category']})
        - Місто: {business_data['city']}
        - Сайт: {'Є' if has_website else 'НЕМАЄ'}
        - Соцмережі: {'Є' if has_socials else 'НЕМАЄ'}
        - Продукт для продажу: {business_data['product']}

        Вимоги до офферу (pitch_message):
        - Привітання, коротка похвала бізнесу або точкове попадання в біль.
        - Конкретна пропозиція (що ми пропонуємо розробити і яку проблему це вирішить).
        - М'який заклик до дії (наприклад: "Цікаво подивитися приклад?" або "Надіслати коротке демо?").
        - Без довгої "води", дружній та професійний тон.

        Поверни JSON:
        {{
            "heat_score": 9,
            "pain_point": "Відсутній онлайн-запис, втрачають вечірні заявки",
            "pitch_message": "Вітаю! Помітив ваш сервіс у м. {business_data['city']}, чудова робота. Зазвичай подібні бізнеси втрачають до 30% клієнтів увечері, бо люди не хочуть дзвонити. Ми розробляємо рішення із записом 24/7. Надіслати приклад?",
            "recommended_price": 5000
        }}
        """

        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logging.error(f"GPT Error: {e}")
            return {
                "heat_score": 6,
                "pain_point": "Потребує автоматизації заяв та нових клієнтів",
                "pitch_message": f"Доброго дня! Помітив вашу компанію {business_data['name']}. Ми розробляємо рішення для автоматизації продажів у ніші {business_data['category']}. Підкажіть, чи актуально зараз збільшити потік заявок?",
                "recommended_price": 4000
            }


hunter = SmartLeadHunter()


# =====================================================================
# LOGIC & SCANNER
# =====================================================================
async def send_lead_to_all_managers(business: Dict, contacts: Dict, analysis: Dict):
    has_website = "✅ Так" if contacts.get('website') else "❌ Ні (Чудова нагода!)"

    buttons = []
    if contacts['phone']:
        for phone in contacts['phone'][:1]:
            buttons.append([InlineKeyboardButton(text=f"📞 {phone}", url=f"tel:{phone}")])
    if contacts['socials'].get('telegram'):
        buttons.append([InlineKeyboardButton(text="✈️ Telegram", url=contacts['socials']['telegram'])])
    if contacts['socials'].get('instagram'):
        buttons.append([InlineKeyboardButton(text="📸 Instagram", url=contacts['socials']['instagram'])])
    if contacts['socials'].get('tiktok'):
        buttons.append([InlineKeyboardButton(text="🎵 TikTok", url=contacts['socials']['tiktok'])])
    if contacts['website']:
        buttons.append([InlineKeyboardButton(text="🌐 Сайт", url=contacts['website'])])

    markup = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
    pitch_text = analysis.get('pitch_message', 'Доброго дня!')

    msg = f"""🔥 <b>NEW LEAD FOUND</b> 🔥
Score: <b>{analysis['heat_score']}/10</b>

🏢 <b>{business['name']}</b>
📍 {business['city']} | {business['category']}

💰 <b>Потенціал:</b> ~{analysis['recommended_price']} грн
🎯 <b>Що продаємо:</b> {business['product']}

⚠️ <b>Біль:</b> {analysis['pain_point']}

💬 <b>Готове повідомлення (натисни щоб скопіювати):</b>
<code>{pitch_text}</code>

📇 <b>Контакти:</b>
📱 Тел: <code>{', '.join(contacts['phone']) if contacts['phone'] else '-'}</code>
📧 Email: <code>{', '.join(contacts['email']) if contacts['email'] else '-'}</code>
🌐 Сайт: {has_website}
"""

    # Розсилаємо ліда усім доданим користувачам
    for user_id in ALLOWED_USERS:
        try:
            await bot.send_message(user_id, msg, parse_mode="HTML", reply_markup=markup)
        except Exception as e:
            logging.error(f"Send error to {user_id}: {e}")


async def process_lead(niche: Dict, city: str):
    query = f"{niche['name']} {city}"

    try:
        results = await hunter.fast_search(query, max_results=3)

        for url in results:
            if not is_scanning:
                return

            if any(s in url.lower() for s in ['instagram.com', 'tiktok.com']):
                business_name = url.split('/')[-1].replace('@', '')
                if not business_name or len(business_name) < 3:
                    continue
            else:
                business_name = niche['name'].title()

            business_data = {
                "name": business_name,
                "category": niche['name'],
                "city": city,
                "product": niche['product']
            }

            contacts = await hunter.find_contacts_deep(business_name, city)
            if not contacts['phone'] and not contacts['email'] and not contacts['socials']:
                continue

            analysis = await hunter.analyze_with_gpt(business_data, contacts)

            if analysis['heat_score'] < 5:
                continue
            if analysis.get('recommended_price', 0) < user_filters['min_price']:
                continue

            await send_lead_to_all_managers(business_data, contacts, analysis)
            await asyncio.sleep(0.5)

    except Exception as e:
        logging.error(f"Error processing {niche['name']} in {city}: {e}")


async def scanner_loop():
    global is_scanning
    await hunter.init_session()

    while is_scanning:
        cities_to_scan = user_filters['cities'] if user_filters['cities'] else ALL_CITIES
        niches_to_scan = [n for n in ALL_NICHES if n['cat'] in user_filters['categories']] if user_filters[
            'categories'] else ALL_NICHES

        random.shuffle(cities_to_scan)
        random.shuffle(niches_to_scan)

        for city in cities_to_scan:
            if not is_scanning:
                break
            for niche in niches_to_scan:
                if not is_scanning:
                    break

                logging.info(f"Scanning: {niche['name']} in {city}")
                await process_lead(niche, city)
                await asyncio.sleep(1)


# =====================================================================
# AUTH & MANAGEMENT
# =====================================================================
def is_authorized(user_id: int) -> bool:
    return user_id in ALLOWED_USERS


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Зберігаємо username при першому старті
    if message.from_user.username:
        USERNAMES_MAP[f"@{message.from_user.username.lower()}"] = message.from_user.id

    if not is_authorized(message.from_user.id):
        await message.answer("❌ У вас немає доступу до цього бота. Зверніться до адміністратора.")
        return

    await message.answer("🚀 <b>Smart Lead Hunter Bot</b> готовий до роботи.", reply_markup=control_keyboard,
                         parse_mode="HTML")


@dp.message(Command("add_manager"))
async def add_manager_cmd(message: types.Message):
    if message.from_user.id != ADMIN_CHAT_ID:
        await message.answer("❌ Ця команда доступна лише головному адміністратору.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "⚠️ Вкажіть Telegram ID або @username менеджеру.\nПриклад:\n`/add_manager @username` або `/add_manager 123456789`",
            parse_mode="Markdown")
        return

    target = args[1].strip()

    if target.isdigit():
        user_id = int(target)
        ALLOWED_USERS.add(user_id)
        await message.answer(f"✅ Менеджера з ID <code>{user_id}</code> додано!", parse_mode="HTML")
    elif target.startswith("@"):
        username = target.lower()
        if username in USERNAMES_MAP:
            user_id = USERNAMES_MAP[username]
            ALLOWED_USERS.add(user_id)
            await message.answer(f"✅ Менеджера {target} додано!", parse_mode="HTML")
        else:
            await message.answer(
                f"⚠️ Менеджер {target} ще не натискав /start у боті. Попросіть його спочатку написати боту /start, після чого повторіть команду.")
    else:
        await message.answer("❌ Некоректний формат. Вкажіть ID або @username.")


@dp.message(Command("del_manager"))
async def del_manager_cmd(message: types.Message):
    if message.from_user.id != ADMIN_CHAT_ID:
        await message.answer("❌ Ця команда доступна лише головному адміністратору.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("⚠️ Вкажіть Telegram ID або @username.\nПриклад: `/del_manager @username`",
                             parse_mode="Markdown")
        return

    target = args[1].strip()
    user_id = None

    if target.isdigit():
        user_id = int(target)
    elif target.startswith("@") and target.lower() in USERNAMES_MAP:
        user_id = USERNAMES_MAP[target.lower()]

    if user_id and user_id in ALLOWED_USERS:
        if user_id == ADMIN_CHAT_ID:
            await message.answer("❌ Ви не можете видалити самі себе!")
            return
        ALLOWED_USERS.remove(user_id)
        await message.answer(f"🗑 Менеджера видалено з системи.")
    else:
        await message.answer("❌ Користувача не знайдено серед активних менеджерів.")


@dp.message(F.text == "👥 Менеджери")
async def list_managers(message: types.Message):
    if not is_authorized(message.from_user.id):
        return

    users_str = "\n".join(
        [f"• <code>{uid}</code> {'(Адмін)' if uid == ADMIN_CHAT_ID else ''}" for uid in ALLOWED_USERS])
    text = f"👥 <b>Авторизовані користувачі ({len(ALLOWED_USERS)}):</b>\n\n{users_str}\n\n<b>Команди для Адміна:</b>\n• <code>/add_manager @username</code>\n• <code>/del_manager @username</code>"
    await message.answer(text, parse_mode="HTML")


# =====================================================================
# FILTERS UI & TELEGRAM HANDLERS
# =====================================================================
def get_filters_inline_keyboard():
    keyboard = []
    for cat_key, cat_name in CATEGORIES.items():
        status = "✅" if cat_key in user_filters['categories'] else "❌"
        keyboard.append([InlineKeyboardButton(text=f"{status} {cat_name}", callback_data=f"toggle_cat:{cat_key}")])

    city_status = "Всі міста" if not user_filters['cities'] else f"Обрано: {len(user_filters['cities'])}"
    keyboard.append([InlineKeyboardButton(text=f"🏙 Міста: ({city_status})", callback_data="open_cities_menu")])

    price_label = f"💰 Мін. чек: {user_filters['min_price']} грн"
    keyboard.append([InlineKeyboardButton(text=price_label, callback_data="change_price")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@dp.message(F.text == "⚙️ Налаштувати фільтри")
async def show_filters(message: types.Message):
    if not is_authorized(message.from_user.id):
        return
    await message.answer("⚙️ <b>Налаштування фільтрів пошуку:</b>\n\nОберіть напрямки, міста та мінімальний чек:",
                         reply_markup=get_filters_inline_keyboard(), parse_mode="HTML")


@dp.callback_query(F.data.startswith("toggle_cat:"))
async def toggle_category(callback: types.CallbackQuery):
    if not is_authorized(callback.from_user.id):
        return
    cat_key = callback.data.split(":")[1]
    if cat_key in user_filters['categories']:
        user_filters['categories'].remove(cat_key)
    else:
        user_filters['categories'].append(cat_key)
    await callback.message.edit_reply_markup(reply_markup=get_filters_inline_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "change_price")
async def change_price_filter(callback: types.CallbackQuery):
    if not is_authorized(callback.from_user.id):
        return
    prices = [0, 3000, 5000, 8000]
    curr_idx = prices.index(user_filters['min_price']) if user_filters['min_price'] in prices else 0
    next_idx = (curr_idx + 1) % len(prices)
    user_filters['min_price'] = prices[next_idx]
    await callback.message.edit_reply_markup(reply_markup=get_filters_inline_keyboard())
    await callback.answer(f"Мін. чек: {user_filters['min_price']} грн")


@dp.callback_query(F.data == "open_cities_menu")
async def open_cities_menu(callback: types.CallbackQuery):
    if not is_authorized(callback.from_user.id):
        return
    keyboard = []
    row = []
    for city in ALL_CITIES[:12]:
        status = "✅" if city in user_filters['cities'] else ""
        row.append(InlineKeyboardButton(text=f"{status} {city}", callback_data=f"toggle_city:{city}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(text="🔄 Скинути міста (Шукати скрізь)", callback_data="reset_cities")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_filters")])

    await callback.message.edit_text("🏙 <b>Оберіть конкретні міста для пошуку:</b>",
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")


@dp.callback_query(F.data.startswith("toggle_city:"))
async def toggle_city(callback: types.CallbackQuery):
    if not is_authorized(callback.from_user.id):
        return
    city = callback.data.split(":")[1]
    if city in user_filters['cities']:
        user_filters['cities'].remove(city)
    else:
        user_filters['cities'].append(city)
    await open_cities_menu(callback)


@dp.callback_query(F.data == "reset_cities")
async def reset_cities(callback: types.CallbackQuery):
    if not is_authorized(callback.from_user.id):
        return
    user_filters['cities'] = []
    await open_cities_menu(callback)


@dp.callback_query(F.data == "back_to_filters")
async def back_to_filters(callback: types.CallbackQuery):
    if not is_authorized(callback.from_user.id):
        return
    await callback.message.edit_text("⚙️ <b>Налаштування фільтрів пошуку:</b>",
                                     reply_markup=get_filters_inline_keyboard(), parse_mode="HTML")


@dp.message(F.text == "🚀 Запустити Mass Scan")
async def start_search(message: types.Message):
    if not is_authorized(message.from_user.id):
        return
    global is_scanning, scan_task
    if is_scanning:
        await message.answer("⚠️ Пошук вже працює!")
        return

    is_scanning = True
    scan_task = asyncio.create_task(scanner_loop())

    cats = ", ".join([CATEGORIES[c] for c in user_filters['categories']]) if user_filters[
        'categories'] else "Усі напрямки"
    cities = ", ".join(user_filters['cities']) if user_filters['cities'] else "Усі міста"

    await message.answer(
        f"✅ <b>Пошук розпочато!</b>\n\n📌 <b>Напрямки:</b> {cats}\n🏙 <b>Міста:</b> {cities}\n💰 <b>Мін. чек:</b> від {user_filters['min_price']} грн",
        parse_mode="HTML")


@dp.message(F.text == "⏹ Зупинити")
async def stop_search(message: types.Message):
    if not is_authorized(message.from_user.id):
        return
    global is_scanning
    is_scanning = False
    await message.answer("🛑 Пошук зупинено.")


async def main():
    try:
        await dp.start_polling(bot)
    finally:
        await hunter.close()


if __name__ == "__main__":
    asyncio.run(main())
