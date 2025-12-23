import asyncio
import json
import logging
import os
import re
import sqlite3
import time
from collections import deque
from typing import Optional, Dict, Any
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-webapp-url.com")
USDT_WALLET = os.getenv("USDT_WALLET")
BTC_WALLET = os.getenv("BTC_WALLET")

# Проверка обязательных переменных
if not TOKEN:
    logging.error("TOKEN is not set in .env file")
    exit(1)

if not ADMIN_ID:
    logging.warning("ADMIN_ID is not set in .env file")

if not USDT_WALLET or USDT_WALLET == "В":
    logging.warning("USDT_WALLET is not properly set in .env file")

# Оптимизация: задаем настройки бота для производительности
default = DefaultBotProperties(parse_mode="Markdown")
bot = Bot(token=TOKEN, default=default)
dp = Dispatcher()

# --- ОПТИМИЗАЦИЯ ПАМЯТИ ---
class OptimizedCache:
    """Оптимизированный кэш для быстрого доступа"""
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.access_order = deque(maxlen=max_size)
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            self.hits += 1
            # Обновляем порядок доступа
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        self.misses += 1
        return None
    
    def set(self, key: str, value: Any):
        if len(self.cache) >= self.max_size:
            # Удаляем самый старый элемент
            oldest = self.access_order.popleft()
            del self.cache[oldest]
        self.cache[key] = value
        self.access_order.append(key)
    
    def stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0
        return {
            "size": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate
        }

# Инициализация кэшей
message_cache = OptimizedCache(max_size=500)
user_language_cache = OptimizedCache(max_size=1000)
response_cache = OptimizedCache(max_size=500)

# --- ЛЕГКАЯ БАЗА ДАННЫХ ---
DATABASE = "nova_bot.db"

def init_db():
    """Инициализация базы данных (синхронная)"""
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")  # Для лучшей производительности
    conn.execute("PRAGMA synchronous=NORMAL")  # Баланс производительности и надежности
    conn.execute("PRAGMA cache_size=2000")  # Увеличиваем кэш
    
    # Таблица для быстрого хранения последних заказов
    conn.execute('''
        CREATE TABLE IF NOT EXISTS quick_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            cart_data TEXT,
            total REAL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Индексы для быстрого поиска
    conn.execute('CREATE INDEX IF NOT EXISTS idx_user_created ON quick_orders(user_id, created_at)')
    
    # Таблица для важных сообщений (только контактные запросы и заказы)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS important_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message_type TEXT,
            data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.execute('CREATE INDEX IF NOT EXISTS idx_type_created ON important_messages(message_type, created_at)')
    
    conn.commit()
    conn.close()

def save_order_sync(user_id: int, username: str, cart_data: str, total: float) -> int:
    """Быстрое сохранение заказа"""
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO quick_orders (user_id, username, cart_data, total) VALUES (?, ?, ?, ?)',
        (user_id, username, cart_data, total)
    )
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id

def save_important_message(user_id: int, message_type: str, data: str):
    """Сохранение важных сообщений"""
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    conn.execute(
        'INSERT INTO important_messages (user_id, message_type, data) VALUES (?, ?, ?)',
        (user_id, message_type, data)
    )
    conn.commit()
    conn.close()

# --- БАЗА ЗНАНИЙ (ENGLISH FIRST) ---

KNOWLEDGE_BASE_EN = {
    'greeting': {
        'keywords': ['hello', 'hi', 'hey', 'start', 'good morning', 'good afternoon', '/start', 'hi ', 'hi!', 'hi.'],
        'responses': [
            "🟦 **NOVA SYSTEMS**\n\nHello! I'm a professional automation system for Telegram business.\n\nI specialize in:\n• AI Agents\n• Data Scrapers\n• Community Tools\n\nHow can I assist you today?",
            "👋 **Welcome to NOVA SYSTEMS**\n\nPremium automation solutions for serious businesses.\n\nReady to scale your operations? What are you looking for?"
        ]
    },
    'price': {
        'keywords': ['price', 'cost', 'how much', 'money', 'pricing', 'expensive', 'cheap'],
        'responses': [
            "💰 **Pricing Structure:**\n\n• AI Agents: $290 (Standard) / $890 (Enterprise)\n• Data Scrapers: $250 (Standard) / $750 (Enterprise)\n• Community Tools: $190 (Standard) / $590 (Enterprise)\n\n**All licenses include:**\n- One-time payment\n- Lifetime license\n- Full source code\n- 30-day support",
            "💎 **Investment:**\n\nStandard versions cover most needs. Enterprise adds full customization and priority support.\n\nWhich solution interests you?"
        ]
    },
    'delivery': {
        'keywords': ['delivery', 'when get', 'time', 'timeline', 'how long', 'get it', 'arrive'],
        'responses': [
            "⚡ **Delivery Timeline:**\n\n• Standard versions: 1 business day\n• Enterprise versions: 1-3 business days\n\n**Process:**\n1. Instant payment confirmation (crypto)\n2. System setup (2-4 hours)\n3. Your approval\n4. Full delivery via encrypted Telegram",
            "🚀 **Fast Delivery:**\n\nAverage delivery: 12-24 hours.\n\nIncludes:\n✓ Full source code\n✓ Installation guide\n✓ Configuration files\n✓ Setup assistance\n✓ Private support"
        ]
    },
    'payment': {
        'keywords': ['payment', 'pay', 'crypto', 'usdt', 'ton', 'bitcoin', 'ethereum', 'wallet', 'how pay'],
        'responses': [
            "💳 **Payment System:**\n\nWe accept cryptocurrency only:\n✓ USDT (TRC20/ERC20)\n✓ TON\n✓ Bitcoin\n✓ Ethereum\n\n**Advantages:**\n• Instant confirmation\n• No personal data required\n• Available worldwide\n• Lower fees (save 3-5%)",
            "🔐 **Crypto Payments:**\n\nFast, secure, and private.\n\n**Wallet for payment:**\n`{USDT_WALLET}`\n\n**Bitcoin wallet:**\n`{BTC_WALLET}`\n\nSend transaction hash after payment."
        ]
    },
    'features': {
        'keywords': ['features', 'what can', 'can do', 'capabilities', 'functionality', 'what offer'],
        'responses': [
            "🚀 **Our Solutions:**\n\n🤖 **Automated Agents:**\n• 24/7 customer support\n• Multi-language conversations\n• Context-aware responses\n• 1000+ simultaneous chats\n\n🌐 **Data Scrapers:**\n• Real-time monitoring\n• Anti-detection technology\n• Telegram notifications\n\n👥 **Community Tools:**\n• Automated subscription management\n• Payment processing\n• Anti-spam protection"
        ]
    },
    'custom': {
        'keywords': ['custom', 'customization', 'customize', 'modify', 'tailor', 'specific needs', 'personalize'],
        'responses': [
            "🎨 **Enterprise Customization:**\n\nEnterprise versions are fully customizable:\n\n✓ Custom responses trained on your data\n✓ Brand integration (your style, your voice)\n✓ Special features and unique functionality\n✓ API modifications for your systems\n✓ Priority development for your requests",
            "🔧 **Personalized Solutions:**\n\nWe mold Enterprise versions to your exact requirements. Direct collaboration ensures perfect fit for your business."
        ]
    },
    'tech': {
        'keywords': ['technical', 'requirements', 'server', 'vps', 'hosting', 'setup', 'install'],
        'responses': [
            "🖥️ **Technical Requirements:**\n\n**Minimum (Standard):**\n• VPS with 1GB RAM\n• 10GB storage\n• Basic Linux knowledge\n\n**Recommended (Enterprise):**\n• VPS with 2GB+ RAM\n• 20GB SSD\n• Custom domain (optional)\n\n**We provide:**\n✓ Installation scripts\n✓ Configuration files\n✓ Setup assistance"
        ]
    },
    'support': {
        'keywords': ['support', 'help', 'update', 'updates', 'maintenance', 'warranty'],
        'responses': [
            "🛡️ **Support & Updates:**\n\n**Included for 30 days:**\n✓ Installation assistance\n✓ Configuration help\n✓ Bug fixes\n✓ Basic troubleshooting\n\n**Lifetime benefits:**\n✓ Security updates\n✓ Critical bug fixes\n✓ Community access\n\n**Enterprise adds:**\n✓ Priority 24/7 support\n✓ Direct developer access"
        ]
    },
    'guarantee': {
        'keywords': ['warranty', 'guarantee', 'refund', 'working', 'reliability', 'trust'],
        'responses': [
            "✅ **Our Guarantee:**\n\n30 days of included support. If it doesn't work as described, we fix it.\n\nWe stand behind our code - it's production-ready and battle-tested.",
            "🔒 **Quality Commitment:**\n\nYou receive working solutions, not just code. Any issues within 30 days are resolved promptly."
        ]
    },
    'products': {
        'keywords': ['ai agent', 'scraper', 'community', 'tool', 'product', 'solution'],
        'responses': [
            "📦 **Our Products:**\n\n🤖 **AI Agents ($290/$890)**\nAutomated customer support and sales\n\n🌐 **Data Scrapers ($250/$750)**\nReal-time monitoring and data extraction\n\n👥 **Community Tools ($190/$590)**\nAutomated subscription management\n\nWhich one are you interested in?"
        ]
    }
}

# Минимальные русские ответы (только если пользователь пишет по-русски)
KNOWLEDGE_BASE_RU = {
    'greeting': {
        'keywords': ['привет', 'здравствуйте', 'хай', 'добрый день', 'начать', 'привет ', 'привет!', 'привет.'],
        'responses': [
            "🟦 **NOVA SYSTEMS**\n\nПривет! Я система автоматизации для бизнеса в Telegram.\n\nЧем могу помочь?"
        ]
    },
    'price': {
        'keywords': ['цена', 'стоимость', 'сколько стоит', 'прайс'],
        'responses': [
            "💰 **Цены:**\n\n• AI агенты: $290/$890\n• Скраперы: $250/$750\n• Инструменты сообществ: $190/$590\n\nВсе лицензии бессрочные."
        ]
    },
    'payment': {
        'keywords': ['оплата', 'платеж', 'крипта', 'usdt', 'bitcoin', 'биткоин'],
        'responses': [
            "💳 **Оплата криптовалютой:**\nUSDT, TON, Bitcoin, Ethereum\n\n**Кошелек USDT:**\n`{USDT_WALLET}`\n\n**Кошелек Bitcoin:**\n`{BTC_WALLET}`"
        ]
    }
}

FALLBACK_RESPONSES_EN = [
    "I specialize in business automation. Could you ask about pricing, features, or delivery?",
    "Ask me about our AI agents, data scrapers, or community tools.",
    "For Enterprise versions, we offer complete customization. Would you like details?"
]

FALLBACK_RESPONSES_RU = [
    "Спросите о ценах, функциях или доставке наших решений.",
    "Интересуют AI агенты, скраперы или инструменты сообществ?",
    "Enterprise версии полностью кастомизируются. Рассказать подробнее?"
]

# --- ОПТИМИЗИРОВАННЫЕ ФУНКЦИИ ---

def detect_language_fast(text: str) -> str:
    """Быстрое определение языка"""
    if not text:
        return 'en'
    
    # Проверяем кэш
    cache_key = f"lang_{hash(text[:50])}"
    cached = user_language_cache.get(cache_key)
    if cached:
        return cached
    
    # Быстрая проверка русских символов
    ru_chars = sum(1 for char in text[:100].lower() if 'а' <= char <= 'я' or char == 'ё')
    
    # Если больше 20% русских символов - считаем русским
    sample_len = len(text[:100])
    result = 'ru' if sample_len > 0 and ru_chars > sample_len * 0.2 else 'en'
    user_language_cache.set(cache_key, result)
    return result

def get_intent_fast(text: str, language: str) -> Optional[str]:
    """Быстрое определение намерения"""
    text_lower = text.lower().strip()
    cache_key = f"intent_{language}_{hash(text_lower[:50])}"
    
    # Проверяем кэш
    cached = response_cache.get(cache_key)
    if cached:
        return cached
    
    # Выбираем базу знаний
    knowledge_base = KNOWLEDGE_BASE_RU if language == 'ru' else KNOWLEDGE_BASE_EN
    
    # Быстрый поиск по ключевым словам
    best_intent = None
    best_score = 0
    
    for intent, data in knowledge_base.items():
        for keyword in data['keywords']:
            # Проверяем точное совпадение или вхождение
            if keyword == text_lower or keyword in text_lower:
                score = len(keyword)
                if score > best_score:
                    best_score = score
                    best_intent = intent
                    break  # Достаточно первого совпадения
    
    # Сохраняем в кэш
    response_cache.set(cache_key, best_intent)
    return best_intent if best_score > 2 else None

def get_response(intent: Optional[str], language: str, user_id: int) -> str:
    """Получение ответа с кэшированием"""
    if not intent:
        responses = FALLBACK_RESPONSES_RU if language == 'ru' else FALLBACK_RESPONSES_EN
        return responses[user_id % len(responses)]
    
    knowledge_base = KNOWLEDGE_BASE_RU if language == 'ru' else KNOWLEDGE_BASE_EN
    
    if intent in knowledge_base:
        responses = knowledge_base[intent]['responses']
        response = responses[user_id % len(responses)]
        
        # Заменяем плейсхолдеры
        if USDT_WALLET and USDT_WALLET != "В" and '{USDT_WALLET}' in response:
            response = response.replace('{USDT_WALLET}', USDT_WALLET)
        
        if BTC_WALLET and '{BTC_WALLET}' in response:
            response = response.replace('{BTC_WALLET}', BTC_WALLET)
        
        return response
    
    return FALLBACK_RESPONSES_EN[0]

# --- ОПТИМИЗИРОВАННЫЕ КЛАВИАТУРЫ ---

def get_main_keyboard():
    """Основная клавиатура (только английская)"""
    keyboard_buttons = [
        [KeyboardButton(text="💰 Prices"), KeyboardButton(text="🚀 Delivery")],
        [KeyboardButton(text="💳 Payment"), KeyboardButton(text="🔧 Support")]
    ]
    
    # Добавляем кнопку веб-приложения только если URL корректный
    if WEBAPP_URL and WEBAPP_URL != "https://your-webapp-url.com":
        keyboard_buttons.insert(0, [KeyboardButton(text="⚡ OPEN NOVA SYSTEM", web_app=WebAppInfo(url=WEBAPP_URL))])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True,
        input_field_placeholder="Ask about our solutions..."
    )

def get_products_keyboard():
    """Клавиатура с продуктами"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🤖 AI Agents", callback_data="product_ai")],
            [InlineKeyboardButton(text="🌐 Data Scrapers", callback_data="product_scraper")],
            [InlineKeyboardButton(text="👥 Community Tools", callback_data="product_comm")],
            [InlineKeyboardButton(text="📊 All Pricing", callback_data="all_prices")]
        ]
    )

# --- ОПТИМИЗИРОВАННЫЕ ХЭНДЛЕРЫ ---

@dp.message(Command("start"))
async def start_command(message: types.Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    # Всегда английский интерфейс при старте
    welcome_text = (
        "🟦 **NOVA SYSTEMS**\n\n"
        "Professional Telegram automation solutions.\n\n"
        "**Our products:**\n"
        "• 🤖 AI Agents (Sales & Support)\n"
        "• 🌐 Data Scrapers (Real-time monitoring)\n"
        "• 👥 Community Tools (Subscription management)\n\n"
        "**Key benefits:**\n"
        "✓ One-time payment\n"
        "✓ Lifetime license\n"
        "✓ Full source code\n"
        "✓ 30-day support\n\n"
        "Use the buttons below to explore:"
    )
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    
    # Логирование для администратора
    if ADMIN_ID:
        try:
            await bot.send_message(
                int(ADMIN_ID),
                f"👤 New user started:\n"
                f"ID: {user_id}\n"
                f"Username: @{message.from_user.username or 'None'}\n"
                f"Name: {message.from_user.full_name}"
            )
        except:
            pass  # Игнорируем ошибки отправки админу

@dp.message(F.text == "💰 Prices")
async def show_prices(message: types.Message):
    """Показать цены"""
    response = (
        "💰 **Pricing Overview:**\n\n"
        "🤖 **AI Agents:**\n"
        "• Standard: $290\n"
        "• Enterprise: $890\n\n"
        "🌐 **Data Scrapers:**\n"
        "• Standard: $250\n"
        "• Enterprise: $750\n\n"
        "👥 **Community Tools:**\n"
        "• Standard: $190\n"
        "• Enterprise: $590\n\n"
        "**All licenses include:**\n"
        "- One-time payment\n"
        "- Lifetime use\n"
        "- Full source code\n"
        "- 30-day support\n\n"
        "Select a product for details:"
    )
    
    await message.answer(
        response,
        reply_markup=get_products_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "🚀 Delivery")
async def show_delivery(message: types.Message):
    """Показать информацию о доставке"""
    response = (
        "⚡ **Delivery Process:**\n\n"
        "**Timeline:**\n"
        "• Standard versions: 1 business day\n"
        "• Enterprise versions: 1-3 business days\n\n"
        "**What you receive:**\n"
        "✓ Full source code\n"
        "✓ Installation guide\n"
        "✓ Configuration files\n"
        "✓ Setup assistance (1 hour)\n"
        "✓ Private support access\n\n"
        "Delivery via encrypted Telegram channel."
    )
    
    await message.answer(response, parse_mode="Markdown")

@dp.message(F.text == "💳 Payment")
async def show_payment(message: types.Message):
    """Показать информацию об оплате"""
    wallet_text = ""
    
    if USDT_WALLET and USDT_WALLET != "В":
        wallet_text += f"**USDT Wallet:**\n`{USDT_WALLET}`\n\n"
    else:
        wallet_text += "**USDT Wallet:** Not configured\n\n"
    
    if BTC_WALLET:
        wallet_text += f"**Bitcoin Wallet:**\n`{BTC_WALLET}`\n\n"
    
    response = (
        f"💳 **Payment Information:**\n\n"
        f"**Accepted cryptocurrencies:**\n"
        f"• USDT (TRC20/ERC20)\n"
        f"• TON\n"
        f"• Bitcoin\n"
        f"• Ethereum\n\n"
        f"**Why crypto?**\n"
        f"• Instant confirmation\n"
        f"• No personal data required\n"
        f"• Available worldwide\n"
        f"• Lower fees\n\n"
        f"{wallet_text}"
        f"Send transaction hash after payment."
    )
    
    await message.answer(response, parse_mode="Markdown")

@dp.message(F.text == "🔧 Support")
async def show_support(message: types.Message):
    """Показать информацию о поддержке"""
    response = (
        "🛡️ **Support System:**\n\n"
        "**Included with every purchase:**\n"
        "✓ 30 days technical support\n"
        "✓ Installation assistance\n"
        "✓ Configuration help\n"
        "✓ Bug fixes\n\n"
        "**Lifetime benefits:**\n"
        "✓ Security updates\n"
        "✓ Critical bug fixes\n"
        "✓ Community access\n\n"
        "**Enterprise additional:**\n"
        "✓ Priority 24/7 support\n"
        "✓ Direct developer access\n"
        "✓ Custom feature requests"
    )
    
    await message.answer(response, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("product_"))
async def handle_product_callback(callback: types.CallbackQuery):
    """Обработка колбэков продуктов"""
    product_type = callback.data.split("_")[1]
    
    if product_type == "ai":
        response = (
            "🤖 **AI Agents:**\n\n"
            "**Standard ($290):**\n"
            "• Smart Auto-Reply\n"
            "• Basic Admin Panel\n"
            "• 24-hour context memory\n"
            "• EN & RU languages\n"
            "• Telegram + Web integration\n\n"
            "**Enterprise ($890):**\n"
            "• Advanced responses\n"
            "• Full Dashboard\n"
            "• Unlimited memory\n"
            "• Multi-language\n"
            "• Full customization\n"
            "• All platforms + API"
        )
    elif product_type == "scraper":
        response = (
            "🌐 **Data Scrapers:**\n\n"
            "**Standard ($250):**\n"
            "• 1 target source\n"
            "• Standard speed\n"
            "• CSV/Excel/JSON export\n"
            "• Email alerts\n"
            "• Basic proxy support\n\n"
            "**Enterprise ($750):**\n"
            "• Up to 5 sources\n"
            "• Real-time monitoring\n"
            "• API + Webhooks\n"
            "• Telegram instant alerts\n"
            "• Advanced proxy support\n"
            "• Anti-detect technology"
        )
    elif product_type == "comm":
        response = (
            "👥 **Community Tools:**\n\n"
            "**Standard ($190):**\n"
            "• AI spam filtering\n"
            "• Text + Media welcome\n"
            "• Manual payment verification\n"
            "• Up to 10,000 users\n"
            "• Basic analytics\n\n"
            "**Enterprise ($590):**\n"
            "• Advanced AI spam filter\n"
            "• Custom media welcome\n"
            "• Auto USDT/TON payments\n"
            "• Unlimited users\n"
            "• Advanced analytics\n"
            "• Auto-kick non-payers"
        )
    elif product_type == "all_prices":
        response = (
            "📊 **Complete Pricing:**\n\n"
            "🤖 AI Agents: $290 / $890\n"
            "🌐 Data Scrapers: $250 / $750\n"
            "👥 Community Tools: $190 / $590\n\n"
            "**All versions include:**\n"
            "- One-time payment\n"
            "- Lifetime license\n"
            "- Full source code\n"
            "- 30-day support\n\n"
            "Enterprise adds full customization."
        )
    
    await callback.message.answer(response, parse_mode="Markdown")
    await callback.answer()

@dp.message(F.content_type == "web_app_data")
async def handle_web_app_data(message: types.Message):
    """Обработка данных из веб-приложения"""
    try:
        data = json.loads(message.web_app_data.data)
        user_id = message.from_user.id
        username = message.from_user.username or str(user_id)
        
        if data.get('type') == 'contact':
            # Сохраняем запрос на контакт
            save_important_message(user_id, 'contact_request', json.dumps(data))
            
            await message.answer(
                "👨‍💻 **Developer contact requested**\n\n"
                "Your request has been forwarded to our development team. "
                "They will contact you shortly via Telegram.\n\n"
                "In the meantime, feel free to ask any technical questions.",
                reply_markup=get_main_keyboard()
            )
            
            if ADMIN_ID:
                try:
                    await bot.send_message(
                        int(ADMIN_ID),
                        f"📞 CONTACT REQUEST\n"
                        f"User: @{username}\n"
                        f"ID: {user_id}\n"
                        f"Name: {message.from_user.full_name}"
                    )
                except:
                    pass
            
            return
        
        if data.get('type') == 'order':
            cart_items = data.get('cart', [])
            total = data.get('total', 0)
            
            # Сохраняем заказ
            order_id = save_order_sync(user_id, username, json.dumps(cart_items), total)
            
            # Определяем срок доставки
            has_pro = any(item.get('tier') == 'pro' for item in cart_items)
            delivery_time = "1-3 business days" if has_pro else "1 business day"
            
            wallet = USDT_WALLET if USDT_WALLET and USDT_WALLET != "В" else "WALLET_NOT_CONFIGURED"
            response = (
                f"✅ **ORDER #{order_id} CREATED**\n\n"
                f"**Total: ${total}**\n"
                f"**Delivery: {delivery_time}**\n\n"
                f"💳 **Payment instructions:**\n"
                f"1. Send ${total} to:\n"
                f"`{wallet}`\n"
                f"2. Send transaction hash\n"
                f"3. We activate delivery within 1 hour\n\n"
                f"After payment you'll receive:\n"
                f"✓ Full source code\n"
                f"✓ Installation guide\n"
                f"✓ Private support access"
            )
            
            await message.answer(response, parse_mode="Markdown")
            
            # Уведомление администратору
            if ADMIN_ID:
                try:
                    cart_text = "\n".join([f"- {item.get('name', 'Item')} (${item.get('price', 0)})" for item in cart_items])
                    await bot.send_message(
                        int(ADMIN_ID),
                        f"💰 NEW ORDER #{order_id}\n\n"
                        f"User: @{username}\n"
                        f"Total: ${total}\n"
                        f"Delivery: {delivery_time}\n\n"
                        f"**Items:**\n{cart_text}"
                    )
                except:
                    pass
            
            return
    
    except json.JSONDecodeError:
        await message.answer(
            "⚠️ Invalid data format. Please try again.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Web app data error: {e}")
        await message.answer(
            "⚠️ An error occurred processing your request. Please try again or contact support.",
            parse_mode="Markdown"
        )

@dp.message(F.text)
async def handle_text_message(message: types.Message):
    """Обработка текстовых сообщений"""
    user_text = message.text
    user_id = message.from_user.id
    
    # Проверяем кэш сообщений
    cache_key = f"msg_{user_id}_{hash(user_text[:50])}"
    cached_response = message_cache.get(cache_key)
    
    if cached_response:
        await message.answer(cached_response, parse_mode="Markdown")
        return
    
    # Определяем язык (по умолчанию английский, переключаем только при явном русском)
    language = detect_language_fast(user_text)
    
    # Определяем намерение
    intent = get_intent_fast(user_text, language)
    
    # Получаем ответ
    response = get_response(intent, language, user_id)
    
    # Сохраняем в кэш
    message_cache.set(cache_key, response)
    
    # Отправляем ответ
    await message.answer(response, parse_mode="Markdown")
    
    # Если пользователь пишет по-русски, но мы ответили по-английски, 
    # можно добавить небольшую заметку (опционально)
    if language == 'ru' and intent is None:
        ru_note = "\n\n_Note: You can ask in English for more detailed information._"
        await message.answer(ru_note, parse_mode="Markdown")

@dp.message(F.reply_to_message)
async def handle_admin_reply(message: types.Message):
    """Обработка ответов администратора"""
    if str(message.from_user.id) != ADMIN_ID:
        return
    
    original_text = message.reply_to_message.text or ""
    
    # Ищем ID пользователя в сообщении
    user_id_match = re.search(r'ID: (\d+)', original_text)
    if user_id_match:
        user_id = int(user_id_match.group(1))
        
        try:
            await bot.send_message(
                user_id,
                f"👨‍💻 **Message from developer:**\n\n{message.text}"
            )
            await message.answer("✅ Reply sent successfully.")
        except Exception as e:
            await message.answer(f"❌ Error: {str(e)}")

# --- МОНИТОРИНГ И ОПТИМИЗАЦИЯ ---

async def monitor_performance():
    """Мониторинг производительности"""
    while True:
        await asyncio.sleep(300)  # Каждые 5 минут
        
        stats = {
            "message_cache": message_cache.stats(),
            "response_cache": response_cache.stats(),
            "language_cache": user_language_cache.stats(),
        }
        
        logging.info(f"Performance stats: {stats}")
        
        # Отправляем статистику администратору (опционально)
        if ADMIN_ID:
            try:
                stats_text = "\n".join([
                    f"**{name}:** Size: {data['size']}, Hit rate: {data['hit_rate']:.1%}"
                    for name, data in stats.items()
                ])
                await bot.send_message(int(ADMIN_ID), f"📊 Bot Performance:\n\n{stats_text}")
            except Exception as e:
                logging.error(f"Failed to send stats to admin: {e}")

async def cleanup_old_data():
    """Очистка старых данных для оптимизации памяти"""
    while True:
        await asyncio.sleep(3600)  # Каждый час
        
        # Очищаем кэши, сохраняя только свежие данные
        current_time = time.time()
        
        # Можно добавить логику очистки старых записей из БД
        try:
            conn = sqlite3.connect(DATABASE, check_same_thread=False)
            # Удаляем заказы старше 30 дней
            conn.execute("DELETE FROM quick_orders WHERE created_at < datetime('now', '-30 days')")
            # Удаляем старые сообщения
            conn.execute("DELETE FROM important_messages WHERE created_at < datetime('now', '-7 days')")
            conn.commit()
            conn.close()
            logging.info("Old data cleanup completed")
        except Exception as e:
            logging.error(f"Cleanup error: {e}")

async def health_check():
    """Проверка здоровья бота"""
    while True:
        await asyncio.sleep(60)
        try:
            # Простая проверка - получаем информацию о боте
            bot_info = await bot.get_me()
            logging.debug(f"Bot health check: {bot_info.username} is alive")
        except Exception as e:
            logging.error(f"Bot health check failed: {e}")

# --- ОСНОВНАЯ ФУНКЦИЯ ---

async def main():
    """Основная функция запуска бота"""
    # Инициализация базы данных
    init_db()
    
    bot_info = await bot.get_me()
    logging.info("🚀 Starting NOVA SYSTEMS Bot...")
    logging.info(f"🤖 Bot ID: {bot_info.id}")
    logging.info(f"🤖 Bot Username: @{bot_info.username}")
    logging.info(f"👑 Admin ID: {ADMIN_ID}")
    logging.info(f"🌐 WebApp URL: {WEBAPP_URL}")
    logging.info(f"💰 USDT Wallet: {USDT_WALLET}")
    logging.info(f"₿ Bitcoin Wallet: {BTC_WALLET}")
    
    # Проверка WebApp URL
    if WEBAPP_URL == "https://your-webapp-url.com":
        logging.warning("⚠️ WebApp URL is set to default value. Mini app button may not work.")
    elif not WEBAPP_URL.startswith(("http://", "https://")):
        logging.error("❌ WebApp URL must start with http:// or https://")
    
    # Запускаем фоновые задачи
    asyncio.create_task(monitor_performance())
    asyncio.create_task(cleanup_old_data())
    asyncio.create_task(health_check())
    
    # Уведомление администратору
    if ADMIN_ID:
        try:
            await bot.send_message(
                int(ADMIN_ID),
                "🟢 **NOVA SYSTEMS Bot Started**\n\n"
                "✅ Database initialized\n"
                "✅ Caching systems ready\n"
                "✅ Performance monitoring active\n"
                "✅ Ready for high load"
            )
        except:
            logging.warning("Could not send startup message to admin")
    
    # Запускаем бота
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Оптимизация: ограничиваем количество обновлений в секунду
    await dp.start_polling(
        bot, 
        allowed_updates=dp.resolve_used_update_types(),
        # Ограничиваем для оптимизации производительности
        polling_timeout=30,
        close_bot_session=False  # Не закрываем сессию при перезапуске
    )

if __name__ == "__main__":
    # Устанавливаем лимиты для оптимизации памяти
    import resource
    try:
        # Увеличиваем лимит открытых файлов (полезно для многих соединений)
        resource.setrlimit(resource.RLIMIT_NOFILE, (4096, 4096))
    except:
        pass
    
    # Запускаем бота с обработкой ошибок
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        # Попытка уведомить администратора
        if ADMIN_ID:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(bot.send_message(int(ADMIN_ID), f"❌ Bot crashed: {str(e)[:100]}"))
                loop.close()
            except:
                pass