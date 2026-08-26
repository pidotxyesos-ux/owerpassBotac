import asyncio
import json
import logging
import os
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
# Секрети краще тримати в змінних оточення, а не в коді.
# Якщо змінна оточення не задана — використовується значення нижче (як було раніше).
# =====================================================================
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8628836250:AAFu3eHYTLa9hYtwBBiUemVkPmF_vEDrXos")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "8984958620"))  # Ваш особистий Telegram ID

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

ALLOWED_USERS = set([ADMIN_CHAT_ID])
USERNAMES_MAP = {}

# =====================================================================
# PER-USER SESSIONS
# =====================================================================
user_sessions: Dict[int, dict] = {}


def get_session(user_id: int) -> dict:
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "scanning": False,
            "task": None,
            "filters": {
                "categories": [],
                "cities": [],
                "min_price": 0
            },
            "seen_leads": set(),
            "seen_urls": set(),
        }
    return user_sessions[user_id]


# =====================================================================
# НІШІ ТА КАТЕГОРІЇ
# Прибрано ніші, власники яких зазвичай самі здатні зробити собі сайт/бота
# (айтішники, розробники автоматизацій) — їм наш оффер нецікавий.
# =====================================================================
CATEGORIES = {
    "construction": "🏗 Будівництво та ремонт",
    "auto": "🚗 Авто та логістика",
    "b2b": "⚖️ Юриспруденція та B2B",
    "services": "📦 Оренда та послуги",
    "med": "🏥 Медицина та спец-послуги"
}

ALL_NICHES = [
    {"name": "ремонт квартир під ключ", "cat": "construction", "product": "site_calc"},
    {"name": "монтаж та продаж сонячних станцій", "cat": "construction", "product": "site_calc"},
    {"name": "будівництво каркасних будинків", "cat": "construction", "product": "portfolio_site"},
    {"name": "установка теплових насосів та опалення", "cat": "construction", "product": "site_calc"},
    {"name": "монтаж натяжних стель", "cat": "construction", "product": "bot_calc"},
    {"name": "дизайн інтер'єру та ремонт", "cat": "construction", "product": "portfolio_site"},
    {"name": "буріння свердловин на воду", "cat": "construction", "product": "landing_page"},
    {"name": "виготовлення та монтаж алюмінієвих вікон і дверей", "cat": "construction", "product": "site_calc"},

    {"name": "детейлінг та захисні плівки", "cat": "auto", "product": "site_calc"},
    {"name": "автопідбір під ключ з Європи та США", "cat": "auto", "product": "bot_quiz"},
    {"name": "оренда комерційної спецтехніки", "cat": "auto", "product": "bot_catalog"},
    {"name": "чип-тюнінг та ретрофіт фар", "cat": "auto", "product": "landing_page"},
    {"name": "реставрація та перетяжка салону авто", "cat": "auto", "product": "photo_estimate_bot"},

    {"name": "продаж мотоциклів та скутерів", "cat": "ecommerce", "product": "bot_catalog"},
    {"name": "продаж квадроциклів та електротранспорту", "cat": "ecommerce", "product": "site_calc"},
    {"name": "магазин запчастин та аксесуарів для авто", "cat": "ecommerce", "product": "site_calc"},
    {"name": "товарка дропшиппінг гаджети та електроніка", "cat": "ecommerce", "product": "bot_catalog"},
    {"name": "продаж тактичного спорядження та екіпіровки", "cat": "ecommerce", "product": "bot_catalog"},
    {"name": "магазин брендового одягу та взуття дроп", "cat": "ecommerce", "product": "site_calc"},
    {"name": "продаж таунхаусів від забудовника", "cat": "ecommerce", "product": "portfolio_site"},

    # Прибрано "впровадження CRM та автоматизація бізнесу" — це вже IT-люди,
    # які або самі зроблять сайт/бота, або мають штат розробників.
    {"name": "бухгалтерський аутсорсинг для ФОП і ТОВ", "cat": "b2b", "product": "site_calc"},
    {"name": "рекрутингове агентство та підбір персоналу", "cat": "b2b", "product": "b2b_landing"},
    {"name": "оренда рекламних білбордів тасілайтів", "cat": "b2b", "product": "bot_catalog"},
    {"name": "складський аутсорсинг та фулфілмент", "cat": "b2b", "product": "b2b_landing"},

    {"name": "меблі на замовлення кухні шафи", "cat": "services", "product": "site_calc"},
    {"name": "професійна хімчистка меблів вдома", "cat": "services", "product": "photo_estimate_bot"},
    {"name": "генеральний клінінг квартир і офісів", "cat": "services", "product": "bot_calc"},
    {"name": "монтаж систем відеонагляду та безпеки", "cat": "services", "product": "site_calc"},
    {"name": "виготовлення корпусних меблів", "cat": "services", "product": "portfolio_site"},

    {"name": "стоматологія імплантація та брекети", "cat": "med", "product": "booking_bot"},
    {"name": "офтальмологічна клініка лазерна корекція", "cat": "med", "product": "booking_bot"},
    {"name": "косметологія та апаратна епіляція", "cat": "med", "product": "booking_bot"},
    {"name": "приватний центр МРТ діагностики", "cat": "med", "product": "booking_bot"}
]

ALL_CITIES = [
    "Київ", "Львів", "Одеса", "Дніпро", "Харків",
    "Вінниця", "Івано-Франківськ", "Тернопіль", "Чернівці",
    "Запоріжжя", "Полтава", "Черкаси", "Житомир", "Хмельницький",
    "Рівне", "Луцьк", "Ужгород"
]

control_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚀 Запустити пошук"), KeyboardButton(text="⏹ Зупинити")],
        [KeyboardButton(text="⚙️ Фільтри"), KeyboardButton(text="👥 Менеджери")]
    ],
    resize_keyboard=True
)

# =====================================================================
# ФІЛЬТРАЦІЯ СМІТТЯ: вакансії, reels/tiktok-відео без прив'язки до бізнесу
# =====================================================================
VACANCY_KEYWORDS = [
    "вакансі", "вакансия", "шукаємо співробітника", "шукаємо менеджера",
    "потрібен продавец", "потрібна людина в команду", "запрошуємо в команду",
    "резюме на пошту", "офіційне працевлаштування", "графік роботи",
    "з/п від", "заробітна плата від", "hh.ua", "rabota.ua",
    "vacancy", "hiring", "we are hiring", "send your cv"
]

SOCIAL_PROFILE_JUNK = {"reel", "reels", "p", "tv", "explore", "stories", "accounts", "video", "tag", "hashtag"}


def looks_like_vacancy(title: str, snippet: str) -> bool:
    text = f"{title} {snippet}".lower()
    return any(kw in text for kw in VACANCY_KEYWORDS)


def normalize_social_or_skip(url: str, source: str) -> Optional[str]:
    """Пошук по Instagram/TikTok часто повертає окремі reels/відео, а не сторінку
    бізнесу. Ми зводимо такі посилання до профілю (щоб проаналізувати саме
    сторінку бізнесу, а не одне відео), або відкидаємо кандидата, якщо
    прив'язати відео до конкретного профілю неможливо."""
    if source == "instagram":
        m = re.search(r'instagram\.com/([A-Za-z0-9_.]+)/(reel|reels|p|tv)/', url)
        if m:
            username = m.group(1)
            if username.lower() in SOCIAL_PROFILE_JUNK:
                return None
            return f"https://www.instagram.com/{username}/"
        if re.search(r'instagram\.com/(reel|reels|p|tv|stories|explore)/', url):
            return None  # відео/пост без імені користувача в URL — не бізнес-профіль
        m2 = re.search(r'instagram\.com/([A-Za-z0-9_.]+)/?(?:\?.*)?$', url)
        if m2:
            username = m2.group(1)
            if username.lower() in SOCIAL_PROFILE_JUNK:
                return None
            return f"https://www.instagram.com/{username}/"
        return None

    if source == "tiktok":
        m = re.search(r'tiktok\.com/(@[A-Za-z0-9_.]+)/video/', url)
        if m:
            return f"https://www.tiktok.com/{m.group(1)}"
        m2 = re.search(r'tiktok\.com/(@[A-Za-z0-9_.]+)/?(?:\?.*)?$', url)
        if m2:
            return f"https://www.tiktok.com/{m2.group(1)}"
        return None

    return url


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

    async def raw_search(self, query: str, max_results: int = 5) -> List[Dict]:
        def _search():
            logging.getLogger("ddgs").setLevel(logging.ERROR)
            logging.getLogger("duckduckgo_search").setLevel(logging.ERROR)
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, region='uk-ua', safesearch='off',
                                             max_results=max_results, backend='duckduckgo'))
                    return [r for r in results if isinstance(r, dict) and 'href' in r]
            except Exception:
                try:
                    with DDGS() as ddgs:
                        results = list(ddgs.text(query, region='uk-ua', max_results=max_results, backend='html'))
                        return [r for r in results if isinstance(r, dict) and 'href' in r]
                except Exception as inner_e:
                    logging.error(f"Search failed for '{query}': {inner_e}")
                    return []

        return await asyncio.to_thread(_search)

    async def multi_source_search(self, niche_name: str, city: str) -> List[Dict]:
        """Шукає в кількох джерелах: веб, Instagram, TikTok, Google Maps,
        фриланс/бізнес-майданчики. Reels/TikTok-відео зводяться до профілю
        бізнесу (або відкидаються, якщо профіль встановити неможливо)."""
        base_query = f"{niche_name} {city}"
        query_plan = [
            (base_query, "web"),
            (f"{base_query} site:instagram.com", "instagram"),
            (f"{base_query} site:tiktok.com", "tiktok"),
            (f"{base_query} google maps", "maps"),
            (f"{base_query} site:freelancehunt.com", "freelance"),
            (f"{base_query} site:work.ua", "freelance"),
            (f"{base_query} site:kabanchik.ua", "freelance"),
            (f"{base_query} site:prom.ua", "freelance"),
        ]

        all_results = []
        seen_urls_local = set()

        for query, source in query_plan:
            results = await self.raw_search(query, max_results=4)
            for r in results:
                raw_url = r.get("href")
                if not raw_url:
                    continue

                title = r.get("title", "") or ""
                snippet = r.get("body", "") or ""

                # відкидаємо вакансії одразу, ще на етапі видачі
                if looks_like_vacancy(title, snippet):
                    continue

                if source in ("instagram", "tiktok"):
                    normalized = normalize_social_or_skip(raw_url, source)
                    if not normalized:
                        continue  # reel/відео без прив'язки до профілю — скіп
                    url = normalized
                else:
                    url = raw_url

                if url in seen_urls_local:
                    continue
                seen_urls_local.add(url)
                all_results.append({
                    "url": url,
                    "snippet": snippet,
                    "title": title,
                    "source": source
                })
            await asyncio.sleep(0.2)

        return all_results

    async def fetch_page_content(self, url: str) -> Optional[str]:
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=6)) as resp:
                if resp.status == 200:
                    return await resp.text()
        except Exception:
            return None
        return None

    def extract_phones(self, text: str) -> List[str]:
        """Номери в біо часто пишуть з пробілами/дужками/дефісами
        (напр. '+380 (63) 123-45-67' або '063 123 45 67') — стара версія
        ловила лише злиті цифри й пропускала майже все з соцмереж."""
        if not text:
            return []
        pattern = r'(?:\+?38)?[\s\-]?\(?0\d{2}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b'
        phones = []
        for match in re.findall(pattern, text):
            clean_num = re.sub(r'\D', '', match)
            if len(clean_num) == 12 and clean_num.startswith('380'):
                phones.append(f"+{clean_num}")
            elif len(clean_num) == 10 and clean_num.startswith('0'):
                phones.append(f"+38{clean_num}")
        return list(dict.fromkeys(phones))[:3]

    def extract_emails(self, text: str) -> List[str]:
        if not text:
            return []
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        return list(dict.fromkeys(re.findall(pattern, text)))[:3]

    def extract_bare_domain(self, text: str) -> Optional[str]:
        """Ловить домен, написаний просто текстом у біо (без http), напр.
        'сайт: mysite.com.ua' — часто єдиний спосіб дізнатись про сайт із соцмереж."""
        if not text:
            return None
        pattern = r'\b((?:[a-zA-Z0-9-]+\.)+(?:com|net|org|ua|store|shop|site|info|pl|de)(?:\.[a-z]{2})?)\b'
        for m in re.findall(pattern, text, flags=re.IGNORECASE):
            low = m.lower()
            if any(low.endswith(d) for d in ("instagram.com", "tiktok.com", "facebook.com", "t.me", "telegram.me")):
                continue
            return m
        return None

    def extract_meta_description(self, html: str) -> str:
        """Instagram/TikTok часто віддають біо саме в og:description /
        twitter:description мета-тегах, навіть коли сама сторінка вимагає
        логін для перегляду постів. Це найнадійніше джерело телефону/сайту."""
        if not html:
            return ""
        chunks = []
        for prop in ("og:description", "twitter:description", "description"):
            m = re.search(
                rf'<meta[^>]+(?:property|name)=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']',
                html, flags=re.IGNORECASE)
            if m:
                chunks.append(m.group(1))
        title_m = re.search(r'<title[^>]*>([^<]+)</title>', html, flags=re.IGNORECASE)
        if title_m:
            chunks.append(title_m.group(1))
        return " ".join(chunks)

    def classify_url(self, url: str, contacts: Dict):
        url_lower = url.lower()
        if "instagram.com" in url_lower:
            contacts["socials"]["instagram"] = url
        elif "tiktok.com" in url_lower:
            contacts["socials"]["tiktok"] = url
        elif "facebook.com" in url_lower:
            contacts["socials"]["facebook"] = url
        elif "t.me/" in url_lower or "telegram.me" in url_lower:
            contacts["socials"]["telegram"] = url
        elif "google.com/maps" in url_lower or "maps.app.goo.gl" in url_lower:
            contacts["socials"]["maps"] = url
        elif any(x in url_lower for x in ["linktr.ee", "taplink", "hi.link", "mssg.me", "bio.link"]):
            contacts["socials"]["linkinbio"] = url
        elif any(x in url_lower for x in ["freelancehunt.com", "work.ua", "kabanchik.ua", "prom.ua"]):
            contacts["socials"]["listing"] = url
        elif not contacts.get("website"):
            contacts["website"] = url

    async def analyze_website_presence(self, contacts: Dict, bio_text: str) -> str:
        """Визначає статус сайту: 'yes' (є робочий сайт), 'no' (немає взагалі),
        'broken' (домен вказаний, але не відкривається/порожній — теж хороша
        зачіпка для офферу)."""
        if not contacts.get("website"):
            bare_domain = self.extract_bare_domain(bio_text)
            if bare_domain:
                contacts["website"] = f"https://{bare_domain}"
            else:
                return "no"

        page_content = await self.fetch_page_content(contacts["website"])
        if page_content and len(page_content) > 300:
            return "yes"
        return "broken"

    async def find_contacts_for_candidate(self, business_name: str, city: str, candidate: Dict) -> Dict:
        """Збирає контакти для кандидата. Для Instagram/TikTok профілів робить
        додатковий пошук саме по сторінці профілю, бо там найчастіше і вказаний
        телефон/сайт у біо."""
        contacts = {"phone": [], "email": [], "socials": {}, "website": None}
        self.classify_url(candidate["url"], contacts)

        bio_chunks = [f"{candidate.get('title', '')} {candidate.get('snippet', '')}"]
        profile_meta_text = ""

        if candidate["source"] in ("instagram", "tiktok"):
            # 1) Пряме звернення до сторінки профілю — головне джерело біо/телефону.
            #    (Раніше тут помилково передавали URL як пошуковий запит у DDGS,
            #    що майже завжди повертало порожнечу.)
            profile_html = await self.fetch_page_content(candidate["url"])
            profile_meta_text = self.extract_meta_description(profile_html)
            if profile_meta_text:
                bio_chunks.append(profile_meta_text)

            # 2) Додатково — пошук за іменем профілю, як резерв, якщо прямий фетч не вдався
            #    (Instagram інколи віддає сторінку логіну без мета-тегів).
            username = candidate["url"].rstrip('/').split('/')[-1].lstrip('@')
            if not profile_meta_text and username:
                backup_results = await self.raw_search(f'"{username}" {candidate["source"]}', max_results=2)
                for r in backup_results:
                    bio_chunks.append(f"{r.get('title', '')} {r.get('body', '')}")

        full_bio_text = " ".join(bio_chunks)
        contacts["phone"].extend(self.extract_phones(full_bio_text))
        contacts["email"].extend(self.extract_emails(full_bio_text))

        # Якщо це звичайний сайт — фетчимо і парсимо HTML
        if contacts["website"]:
            page_content = await self.fetch_page_content(contacts["website"])
            if page_content:
                contacts["phone"].extend(self.extract_phones(page_content))
                contacts["email"].extend(self.extract_emails(page_content))

        # Якщо досі нічого — фінальна спроба прицільним запитом
        if not contacts["phone"] and not contacts["email"]:
            follow_up = await self.raw_search(f"{business_name} {city} телефон номер", max_results=2)
            for r in follow_up:
                text = f"{r.get('title', '')} {r.get('body', '')}"
                contacts["phone"].extend(self.extract_phones(text))
                contacts["email"].extend(self.extract_emails(text))
                if not contacts["website"]:
                    self.classify_url(r.get("href", ""), contacts)

        contacts["phone"] = list(dict.fromkeys(contacts["phone"]))[:3]
        contacts["email"] = list(dict.fromkeys(contacts["email"]))[:3]
        contacts["site_status"] = await self.analyze_website_presence(contacts, full_bio_text)
        return contacts

    async def analyze_with_gpt(self, business_data: Dict, contacts: Dict) -> Dict:
        site_status = contacts.get("site_status", "no")
        site_desc = {
            "yes": "Є робочий сайт",
            "broken": "Домен десь вказаний, але сайт не працює/порожній",
            "no": "Сайту немає взагалі"
        }[site_status]
        has_socials = bool(contacts.get("socials"))

        opener_hint = random.choice([
            "Почни з короткого щирого коментаря про їхній бізнес.",
            "Почни одразу з болю клієнта, без довгого привітання.",
            "Почни з цікавого факту або спостереження про нішу.",
            "Почни просто і по-дружньому, без пафосу."
        ])

        raw_context = business_data.get("raw_context", "")[:600]

        prompt = f"""
        Ти - досвідчений менеджер з продажів IT-послуг (боти, сайти, автоматизація).
        Напиши УНІКАЛЬНЕ (не шаблонне) холодне повідомлення у месенджер для КОНКРЕТНОГО клієнта нижче.
        Формулюй щоразу по-новому: не повторюй структуру речень з попередніх повідомлень,
        варіюй довжину, порядок думок і слова. {opener_hint}
        НЕ використовуй жодних заготовлених фраз-шаблонів — повідомлення повинно звучати так,
        ніби його написала жива людина саме для цього бізнесу, з урахуванням стану його сайту.

        Клієнт:
        - Пошукова ніша: {business_data['name']} ({business_data['category']})
        - Місто: {business_data['city']}
        - Стан сайту: {site_desc}
        - Соцмережі: {'Є' if has_socials else 'НЕМАЄ'}
        - Продукт для продажу: {business_data['product']}
        - Сирі дані зі сторінки/сніпета (назва, біо, título тощо), використай щоб визначити
          РЕАЛЬНУ назву компанії: {raw_context or "немає додаткових даних"}

        Поверни лише JSON, без пояснень:
        {{
            "company_name": "нормальна людська назва компанії, визначена з сирих даних (якщо не вдається — залиши нішу як є)",
            "heat_score": 9,
            "pain_point": "коротко в чому біль клієнта",
            "pitch_message": "готовий текст повідомлення, 3-5 речень, конкретна пропозиція + м'який заклик до дії",
            "recommended_price": 5000
        }}
        """

        last_error = None
        for attempt in range(3):
            try:
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=1.0,
                    response_format={"type": "json_object"}
                )
                raw_content = response.choices[0].message.content or ""
                cleaned = re.sub(r'^```json|```$', '', raw_content.strip(), flags=re.MULTILINE).strip()
                parsed = json.loads(cleaned)
                if not parsed.get("pitch_message"):
                    raise ValueError("GPT повернув порожній pitch_message")
                return parsed
            except Exception as e:
                last_error = e
                logging.error(f"GPT Error (attempt {attempt + 1}): {e}")
                await asyncio.sleep(1)

        # Якщо GPT недоступний — позначаємо лід як "потребує ручної обробки" і
        # шлемо адміну ТОЧНУ причину, щоб не гадати наосліп (найчастіше це
        # невалідний/вичерпаний OPENAI_API_KEY або немає доступу до моделі).
        logging.error(f"GPT остаточно недоступний: {last_error}")
        try:
            await bot.send_message(
                ADMIN_CHAT_ID,
                f"⚠️ <b>GPT не відповів 3 рази поспіль.</b>\nПричина: <code>{str(last_error)[:500]}</code>\n\n"
                f"Найчастіші причини: невірний/прострочений OPENAI_API_KEY, вичерпана квота, немає доступу до моделі gpt-4o-mini.",
                parse_mode="HTML"
            )
        except Exception:
            pass
        return {
            "company_name": business_data['name'],
            "heat_score": 5,
            "pain_point": "не вдалось згенерувати автоматично — потрібен ручний аналіз",
            "pitch_message": "⚠️ ШІ тимчасово недоступний — напишіть повідомлення для цього ліда вручну.",
            "recommended_price": 0,
            "gpt_failed": True
        }


hunter = SmartLeadHunter()


# =====================================================================
# LOGIC & SCANNER
# =====================================================================
def _viber_link(phone: str) -> str:
    return f"viber://chat?number={phone.replace('+', '%2B')}"


def _telegram_guess_link(phone: str) -> str:
    # t.me/+<номер> відкриє чат, якщо у власника дозволено знаходження за номером
    return f"https://t.me/{phone}"


async def send_lead_to_user(user_id: int, business: Dict, contacts: Dict, analysis: Dict):
    site_labels = {"yes": "✅ Є", "broken": "⚠️ Не працює", "no": "❌ Немає (гарна нагода!)"}
    site_status_label = site_labels.get(contacts.get("site_status", "no"), "❌ Немає")

    buttons = []
    row = []
    if contacts['phone']:
        phone = contacts['phone'][0]
        row.append(InlineKeyboardButton(text="📞 Дзвінок", url=f"tel:{phone}"))
        row.append(InlineKeyboardButton(text="💜 Viber", url=_viber_link(phone)))
    if row:
        buttons.append(row)
        row = []

    if contacts['socials'].get('telegram'):
        row.append(InlineKeyboardButton(text="✈️ Telegram", url=contacts['socials']['telegram']))
    elif contacts['phone']:
        row.append(InlineKeyboardButton(text="✈️ Telegram (спроба)", url=_telegram_guess_link(contacts['phone'][0])))
    if contacts['socials'].get('instagram'):
        row.append(InlineKeyboardButton(text="📸 Instagram", url=contacts['socials']['instagram']))
    if row:
        buttons.append(row)
        row = []

    if contacts['socials'].get('tiktok'):
        row.append(InlineKeyboardButton(text="🎵 TikTok", url=contacts['socials']['tiktok']))
    if contacts['socials'].get('maps'):
        row.append(InlineKeyboardButton(text="🗺 Maps", url=contacts['socials']['maps']))
    if row:
        buttons.append(row)
        row = []

    if contacts.get('website'):
        row.append(InlineKeyboardButton(text="🌐 Сайт", url=contacts['website']))
    if contacts['socials'].get('listing'):
        row.append(InlineKeyboardButton(text="📋 Оголошення", url=contacts['socials']['listing']))
    if row:
        buttons.append(row)

    markup = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
    pitch_text = analysis.get('pitch_message', '')
    warn = "\n⚠️ <i>Потребує ручної перевірки — ШІ не згенерував оффер</i>" if analysis.get("gpt_failed") else ""

    phones_str = ", ".join(contacts['phone']) if contacts['phone'] else "—"
    emails_str = ", ".join(contacts['email']) if contacts['email'] else "—"

    msg = (
        f"🔥 <b>{business['name']}</b>\n"
        f"📍 {business['city']} · {business['category']}\n"
        f"⭐ {analysis['heat_score']}/10   💰 ~{analysis['recommended_price']} грн   🌐 Сайт: {site_status_label}\n\n"
        f"<b>Біль:</b> {analysis['pain_point']}{warn}\n\n"
        f"<b>Повідомлення (тап — скопіювати):</b>\n<code>{pitch_text}</code>\n\n"
        f"📱 {phones_str}\n"
        f"📧 {emails_str}"
    )

    try:
        await bot.send_message(user_id, msg, parse_mode="HTML", reply_markup=markup)
    except Exception as e:
        logging.error(f"Send error to {user_id}: {e}")


def make_dedupe_key(business_name: str, city: str, contacts: Dict) -> str:
    if contacts["phone"]:
        return f"phone:{contacts['phone'][0]}"
    if contacts["email"]:
        return f"email:{contacts['email'][0]}"
    return f"name:{business_name.strip().lower()}:{city.lower()}"


async def process_lead_candidate(candidate: Dict, niche: Dict, city: str, user_id: int, session: dict):
    url = candidate["url"]
    if url in session["seen_urls"]:
        return
    session["seen_urls"].add(url)

    if not session["scanning"]:
        return

    if candidate["source"] in ("instagram", "tiktok"):
        business_name = url.rstrip('/').split('/')[-1].lstrip('@').replace('@', '')
        if not business_name or len(business_name) < 3:
            business_name = niche['name'].title()
    else:
        business_name = candidate.get("title") or niche['name'].title()

    business_data = {
        "name": business_name,
        "category": niche['name'],
        "city": city,
        "product": niche['product'],
        # сирий текст (заголовок сторінки, сніпет пошуку, og:description профілю) —
        # саме з нього GPT дістає реальну назву компанії замість шматка URL
        "raw_context": f"{candidate.get('title', '')} | {candidate.get('snippet', '')}"
    }

    contacts = await hunter.find_contacts_for_candidate(business_name, city, candidate)
    if not contacts['phone'] and not contacts['email'] and not contacts['socials']:
        return

    dedupe_key = make_dedupe_key(business_name, city, contacts)
    if dedupe_key in session["seen_leads"]:
        return
    session["seen_leads"].add(dedupe_key)

    analysis = await hunter.analyze_with_gpt(business_data, contacts)
    if analysis.get("company_name") and not analysis.get("gpt_failed"):
        business_data["name"] = analysis["company_name"]

    if not analysis.get("gpt_failed"):
        if analysis['heat_score'] < 5:
            return
        if analysis.get('recommended_price', 0) < session["filters"]['min_price']:
            return

    await send_lead_to_user(user_id, business_data, contacts, analysis)
    await asyncio.sleep(0.5)


async def process_lead(niche: Dict, city: str, user_id: int, session: dict):
    try:
        candidates = await hunter.multi_source_search(niche['name'], city)
        for candidate in candidates:
            if not session["scanning"]:
                return
            await process_lead_candidate(candidate, niche, city, user_id, session)
    except Exception as e:
        logging.error(f"Error processing {niche['name']} in {city} for user {user_id}: {e}")


async def scanner_loop(user_id: int):
    session = get_session(user_id)
    await hunter.init_session()

    while session["scanning"]:
        filters = session["filters"]
        cities_to_scan = filters['cities'] if filters['cities'] else list(ALL_CITIES)
        niches_to_scan = [n for n in ALL_NICHES if n['cat'] in filters['categories']] if filters[
            'categories'] else list(ALL_NICHES)

        random.shuffle(cities_to_scan)
        random.shuffle(niches_to_scan)

        for city in cities_to_scan:
            if not session["scanning"]:
                break
            for niche in niches_to_scan:
                if not session["scanning"]:
                    break

                logging.info(f"[user {user_id}] Scanning: {niche['name']} in {city}")
                await process_lead(niche, city, user_id, session)
                await asyncio.sleep(1)


# =====================================================================
# AUTH & MANAGEMENT
# =====================================================================
def is_authorized(user_id: int) -> bool:
    return user_id in ALLOWED_USERS


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.username:
        USERNAMES_MAP[f"@{message.from_user.username.lower()}"] = message.from_user.id

    if not is_authorized(message.from_user.id):
        await message.answer("❌ У вас немає доступу до цього бота.")
        return

    get_session(message.from_user.id)
    await message.answer(
        "👋 <b>Lead Hunter</b>\n\nЗнаходжу бізнеси без сайту (або з нежиттєздатним сайтом) в Instagram, "
        "TikTok, Google Maps та вебі, і готую персональний оффер.\n\nКожен користувач бачить лише власні ліди.",
        reply_markup=control_keyboard, parse_mode="HTML")


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
        user_sessions.pop(user_id, None)
        await message.answer(f"🗑 Менеджера видалено з системи.")
    else:
        await message.answer("❌ Користувача не знайдено серед активних менеджерів.")


@dp.message(F.text == "👥 Менеджери")
async def list_managers(message: types.Message):
    if not is_authorized(message.from_user.id):
        return

    users_str = "\n".join(
        [f"• <code>{uid}</code> {'(Адмін)' if uid == ADMIN_CHAT_ID else ''}" for uid in ALLOWED_USERS])
    text = f"👥 <b>Авторизовані ({len(ALLOWED_USERS)}):</b>\n\n{users_str}\n\n<code>/add_manager @username</code>\n<code>/del_manager @username</code>"
    await message.answer(text, parse_mode="HTML")


# =====================================================================
# FILTERS UI (per-user)
# =====================================================================
def get_filters_inline_keyboard(session: dict):
    filters = session["filters"]
    keyboard = []
    for cat_key, cat_name in CATEGORIES.items():
        status = "✅" if cat_key in filters['categories'] else "▫️"
        keyboard.append([InlineKeyboardButton(text=f"{status} {cat_name}", callback_data=f"toggle_cat:{cat_key}")])

    city_status = "всі" if not filters['cities'] else f"{len(filters['cities'])} обрано"
    keyboard.append([InlineKeyboardButton(text=f"🏙 Міста: {city_status}", callback_data="open_cities_menu")])

    price_label = f"💰 Мін. чек: {filters['min_price']} грн"
    keyboard.append([InlineKeyboardButton(text=price_label, callback_data="change_price")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@dp.message(F.text == "⚙️ Фільтри")
async def show_filters(message: types.Message):
    if not is_authorized(message.from_user.id):
        return
    session = get_session(message.from_user.id)
    await message.answer("⚙️ <b>Фільтри пошуку</b>", reply_markup=get_filters_inline_keyboard(session), parse_mode="HTML")


@dp.callback_query(F.data.startswith("toggle_cat:"))
async def toggle_category(callback: types.CallbackQuery):
    if not is_authorized(callback.from_user.id):
        return
    session = get_session(callback.from_user.id)
    cat_key = callback.data.split(":")[1]
    if cat_key in session["filters"]['categories']:
        session["filters"]['categories'].remove(cat_key)
    else:
        session["filters"]['categories'].append(cat_key)
    await callback.message.edit_reply_markup(reply_markup=get_filters_inline_keyboard(session))
    await callback.answer()


@dp.callback_query(F.data == "change_price")
async def change_price_filter(callback: types.CallbackQuery):
    if not is_authorized(callback.from_user.id):
        return
    session = get_session(callback.from_user.id)
    prices = [0, 3000, 5000, 8000]
    curr_idx = prices.index(session["filters"]['min_price']) if session["filters"]['min_price'] in prices else 0
    next_idx = (curr_idx + 1) % len(prices)
    session["filters"]['min_price'] = prices[next_idx]
    await callback.message.edit_reply_markup(reply_markup=get_filters_inline_keyboard(session))
    await callback.answer(f"Мін. чек: {session['filters']['min_price']} грн")


@dp.callback_query(F.data == "open_cities_menu")
async def open_cities_menu(callback: types.CallbackQuery):
    if not is_authorized(callback.from_user.id):
        return
    session = get_session(callback.from_user.id)
    keyboard = []
    row = []
    for city in ALL_CITIES[:12]:
        status = "✅" if city in session["filters"]['cities'] else ""
        row.append(InlineKeyboardButton(text=f"{status} {city}", callback_data=f"toggle_city:{city}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(text="🔄 Скинути (шукати скрізь)", callback_data="reset_cities")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_filters")])

    await callback.message.edit_text("🏙 <b>Міста для пошуку</b>",
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")


@dp.callback_query(F.data.startswith("toggle_city:"))
async def toggle_city(callback: types.CallbackQuery):
    if not is_authorized(callback.from_user.id):
        return
    session = get_session(callback.from_user.id)
    city = callback.data.split(":")[1]
    if city in session["filters"]['cities']:
        session["filters"]['cities'].remove(city)
    else:
        session["filters"]['cities'].append(city)
    await open_cities_menu(callback)


@dp.callback_query(F.data == "reset_cities")
async def reset_cities(callback: types.CallbackQuery):
    if not is_authorized(callback.from_user.id):
        return
    session = get_session(callback.from_user.id)
    session["filters"]['cities'] = []
    await open_cities_menu(callback)


@dp.callback_query(F.data == "back_to_filters")
async def back_to_filters(callback: types.CallbackQuery):
    if not is_authorized(callback.from_user.id):
        return
    session = get_session(callback.from_user.id)
    await callback.message.edit_text("⚙️ <b>Фільтри пошуку</b>",
                                     reply_markup=get_filters_inline_keyboard(session), parse_mode="HTML")


@dp.message(F.text == "🚀 Запустити пошук")
async def start_search(message: types.Message):
    if not is_authorized(message.from_user.id):
        return
    user_id = message.from_user.id
    session = get_session(user_id)

    if session["scanning"]:
        await message.answer("⚠️ Пошук вже працює.")
        return

    session["scanning"] = True
    session["task"] = asyncio.create_task(scanner_loop(user_id))

    filters = session["filters"]
    cats = ", ".join([CATEGORIES[c] for c in filters['categories']]) if filters['categories'] else "усі напрямки"
    cities = ", ".join(filters['cities']) if filters['cities'] else "усі міста"

    await message.answer(
        f"✅ <b>Пошук запущено</b>\n📌 {cats}\n🏙 {cities}\n💰 від {filters['min_price']} грн",
        parse_mode="HTML")


@dp.message(F.text == "⏹ Зупинити")
async def stop_search(message: types.Message):
    if not is_authorized(message.from_user.id):
        return
    session = get_session(message.from_user.id)
    session["scanning"] = False
    await message.answer("🛑 Пошук зупинено.")


async def main():
    try:
        await dp.start_polling(bot)
    finally:
        await hunter.close()


if __name__ == "__main__":
    asyncio.run(main())
