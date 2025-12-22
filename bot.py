import asyncio
import json
import logging
import os
import re
import sqlite3
from datetime import datetime
from difflib import SequenceMatcher
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
USDT_WALLET = os.getenv("USDT_WALLET")
WEBAPP_URL = os.getenv("WEBAPP_URL")

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# --- ДАТАБЕЙЗ ---
DATABASE = "nova_bot.db"

# Синхронные функции для работы с SQLite
def init_db_sync():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Таблица сообщений (история чатов)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            message TEXT,
            bot_response TEXT,
            language TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            processed INTEGER DEFAULT 0
        )
    ''')
    
    # Таблица заказов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            cart_data TEXT,
            total REAL,
            status TEXT DEFAULT 'pending',
            payment_hash TEXT,
            delivery_time TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            processed INTEGER DEFAULT 0
        )
    ''')
    
    # Таблица сессий для восстановления состояния
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            user_id INTEGER PRIMARY KEY,
            last_context TEXT,
            last_language TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

async def init_db():
    """Асинхронная инициализация базы данных"""
    await asyncio.get_event_loop().run_in_executor(None, init_db_sync)

def save_message_sync(user_id: int, username: str, message: str, bot_response: str, language: str):
    """Сохранить сообщение в базу (синхронно)"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO messages (user_id, username, message, bot_response, language, processed)
        VALUES (?, ?, ?, ?, ?, 1)
    ''', (user_id, username, message, bot_response, language))
    conn.commit()
    conn.close()

async def save_message(user_id: int, username: str, message: str, bot_response: str, language: str):
    """Сохранить сообщение в базу (асинхронно)"""
    await asyncio.get_event_loop().run_in_executor(
        None, save_message_sync, user_id, username, message, bot_response, language
    )

def save_order_sync(user_id: int, username: str, cart_data: str, total: float, delivery_time: str):
    """Сохранить заказ в базу (синхронно)"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO orders (user_id, username, cart_data, total, delivery_time, processed)
        VALUES (?, ?, ?, ?, ?, 0)
    ''', (user_id, username, cart_data, total, delivery_time))
    conn.commit()
    order_id = cursor.lastrowid
    conn.close()
    return order_id

async def save_order(user_id: int, username: str, cart_data: str, total: float, delivery_time: str):
    """Сохранить заказ в базу (асинхронно)"""
    return await asyncio.get_event_loop().run_in_executor(
        None, save_order_sync, user_id, username, cart_data, total, delivery_time
    )

def get_pending_orders_sync():
    """Получить необработанные заказы (синхронно)"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, user_id, username, cart_data, total, delivery_time 
        FROM orders WHERE processed = 0
    ''')
    orders = cursor.fetchall()
    conn.close()
    return orders

async def get_pending_orders():
    """Получить необработанные заказы (асинхронно)"""
    return await asyncio.get_event_loop().run_in_executor(None, get_pending_orders_sync)

def mark_order_processed_sync(order_id: int):
    """Пометить заказ как обработанный (синхронно)"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('UPDATE orders SET processed = 1 WHERE id = ?', (order_id,))
    conn.commit()
    conn.close()

async def mark_order_processed(order_id: int):
    """Пометить заказ как обработанный (асинхронно)"""
    await asyncio.get_event_loop().run_in_executor(None, mark_order_processed_sync, order_id)

def save_session_sync(user_id: int, context: str, language: str):
    """Сохранить сессию пользователя (синхронно)"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO sessions (user_id, last_context, last_language, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, context, language))
    conn.commit()
    conn.close()

async def save_session(user_id: int, context: str, language: str):
    """Сохранить сессию пользователя (асинхронно)"""
    await asyncio.get_event_loop().run_in_executor(
        None, save_session_sync, user_id, context, language
    )

def get_session_sync(user_id: int):
    """Получить сессию пользователя (синхронно)"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT last_context, last_language FROM sessions WHERE user_id = ?', (user_id,))
    session = cursor.fetchone()
    conn.close()
    return session

async def get_session(user_id: int):
    """Получить сессию пользователя (асинхронно)"""
    return await asyncio.get_event_loop().run_in_executor(None, get_session_sync, user_id)

def get_recent_messages_sync(user_id: int, limit: int = 10):
    """Получить последние сообщения пользователя (синхронно)"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT message, bot_response, timestamp 
        FROM messages 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    ''', (user_id, limit))
    messages = cursor.fetchall()
    conn.close()
    return messages

async def get_recent_messages(user_id: int, limit: int = 10):
    """Получить последние сообщения пользователя (асинхронно)"""
    return await asyncio.get_event_loop().run_in_executor(
        None, get_recent_messages_sync, user_id, limit
    )

# --- БАЗА ЗНАНИЙ БОТА (АНГЛИЙСКАЯ) ---
KNOWLEDGE_BASE_EN = {
    'hello': {
        'keywords': ['hello', 'hi', 'hey', 'start', 'good morning', 'good afternoon'],
        'responses': [
            "🟦 **NOVA SYSTEMS**\n\nHello! I'm a professional automation system for Telegram business.\n\nWhat brings you here today?",
            "👋 **Welcome to NOVA SYSTEMS**\n\nI specialize in premium automation solutions for businesses.\n\nHow can I assist you?"
        ]
    },
    'price': {
        'keywords': ['price', 'cost', 'how much', 'money', 'pricing'],
        'responses': [
            "💰 **Our pricing structure:**\n\n• AI Agents: $290 (Standard) / $890 (Enterprise)\n• Data Scrapers: $250 (Standard) / $750 (Enterprise)\n• Community Tools: $190 (Standard) / $590 (Enterprise)\n\n**Key benefits:**\n- One-time payment (no subscriptions)\n- Lifetime license\n- Full source code\n- 30 days included support\n\nWhich solution fits your needs?",
            "💎 **Value proposition:**\n\nStandard versions cover most use cases. Enterprise adds complete customization and priority support."
        ]
    },
    'delivery': {
        'keywords': ['delivery', 'when get', 'time', 'timeline', 'how long', 'get it'],
        'responses': [
            "⚡ **Delivery process:**\n\n1. **Payment confirmation** (Instant with crypto)\n2. **System setup** (2-4 hours)\n3. **Testing** (Your approval)\n4. **Final delivery** (Source code + documentation)\n\n⏱️ **Delivery timeline:**\n• Standard versions: 1 business day\n• Enterprise versions: 1-3 business days\n\nWe deliver via encrypted Telegram channel.",
            "🚀 **Fast delivery:**\n\nAverage delivery time: 12-24 hours.\n\nDelivery includes:\n✓ Full source code\n✓ Installation guide\n✓ Configuration files\n✓ Setup assistance (1 hour)\n✓ Private support access"
        ]
    },
    'payment': {
        'keywords': ['payment', 'pay', 'crypto', 'usdt', 'ton', 'bitcoin', 'ethereum', 'wallet'],
        'responses': [
            "💳 **Payment system:**\n\nWe accept **cryptocurrency only** for:\n✓ Speed: Seconds confirmation\n✓ Privacy: No personal data\n✓ Global: Available worldwide\n✓ Lower fees: Save 3-5%\n✓ Security: No chargebacks\n\n✅ **Accepted:** USDT (TRC20/ERC20), TON, Bitcoin, Ethereum\n\nFaster delivery, better privacy."
        ]
    },
    'features': {
        'keywords': ['features', 'what can', 'can do', 'capabilities', 'functionality'],
        'responses': [
            "🚀 **NOVA SYSTEMS capabilities:**\n\n🤖 **Automated Agents:**\n• 24/7 customer support\n• Multi-language conversations\n• Context-aware responses\n• Integration with 50+ platforms\n• Handles 1000+ simultaneous chats\n\n🌐 **Data Scrapers:**\n• Real-time monitoring\n• Anti-detection technology\n• Telegram notifications\n• Export to any format\n\n👥 **Community Tools:**\n• Automated subscription management\n• Payment processing\n• Anti-spam protection\n• User analytics\n• Content protection"
        ]
    },
    'custom': {
        'keywords': ['custom', 'customization', 'customize', 'modify', 'tailor', 'specific needs'],
        'responses': [
            "🎨 **Enterprise customization:**\n\nEnterprise versions are fully customizable to your business:\n\n✓ **Custom responses:** Trained on your data\n✓ **Brand integration:** Your style, your voice\n✓ **Special features:** Add unique functionality\n✓ **API modifications:** Adjust to your systems\n✓ **Priority development:** Your requests first\n\nWe work directly with you to ensure perfect fit.",
            "🔧 **Personalized approach:**\n\nWith Enterprise, you get a solution molded to your requirements:\n• Adjust personality and knowledge base\n• Integrate with your CRM\n• Customize reporting format\n• Configure alert systems\n• Adapt interface for your users"
        ]
    },
    'tech': {
        'keywords': ['technical', 'requirements', 'server', 'vps', 'hosting', 'setup'],
        'responses': [
            "🖥️ **Technical requirements:**\n\n**Minimum (Standard):**\n• VPS with 1GB RAM\n• 10GB storage\n• Basic Linux knowledge\n• Telegram account\n\n**Recommended (Enterprise):**\n• VPS with 2GB+ RAM\n• 20GB SSD\n• Docker knowledge (optional)\n• Custom domain\n\n**We provide:**\n✓ Installation scripts\n✓ Configuration files\n✓ Database setup\n✓ SSL certificate guidance"
        ]
    },
    'support': {
        'keywords': ['support', 'help', 'update', 'updates', 'maintenance'],
        'responses': [
            "🛡️ **Support & updates:**\n\n**Included for 30 days:**\n✓ Installation assistance\n✓ Configuration help\n✓ Bug fixes\n✓ Basic troubleshooting\n\n**Lifetime benefits:**\n✓ Security updates\n✓ Critical bug fixes\n✓ Community access\n✓ Documentation updates\n\n**Enterprise adds:**\n✓ Priority 24/7 support\n✓ Direct developer access\n✓ Custom feature requests"
        ]
    },
    'why': {
        'keywords': ['why you', 'difference', 'unique', 'better', 'advantage'],
        'responses': [
            "🏆 **Why choose NOVA SYSTEMS:**\n\n1. **Proven solutions:** Used by businesses worldwide\n2. **No subscriptions:** One payment, lifetime use\n3. **Full transparency:** Complete source code provided\n4. **Enterprise quality:** Code written for scalability\n5. **Direct access:** Work with developers, not support\n6. **Crypto-native:** Built for modern digital economy"
        ]
    },
    'guarantee': {
        'keywords': ['warranty', 'guarantee', 'refund', 'working', 'reliability'],
        'responses': [
            "✅ **Our guarantee:** 30 days of included support. If it doesn't work as described, we fix it.\n\n**Lifetime benefits:**\n✓ Security updates\n✓ Critical bug fixes\n✓ Community access",
            "🔒 **Quality guarantee:**\n\nYou get working solutions, not just code. Any issues within 30 days are resolved.\n\nOur reputation is built on delivering what we promise."
        ]
    },
    'ai_agents': {
        'keywords': ['ai agent', 'ai agents', 'chat bot', 'support bot', 'sales bot'],
        'responses': [
            "🤖 **Automated Agents:**\n\nThese are complete systems that work 24/7:\n\n**Standard ($290):**\n• Smart Auto-Reply\n• Admin Panel (Basic)\n• Context Memory (24 hours)\n• Languages: EN & RU\n• Integration: Telegram + Web\n\n**Enterprise ($890):**\n• Advanced Responses\n• Full Dashboard\n• Unlimited Memory\n• Multi-Language\n• Full Customization\n• All Platforms + API\n\nPerfect for: customer support, sales, lead generation."
        ]
    },
    'scrapers': {
        'keywords': ['scraper', 'parsing', 'data extraction', 'monitoring', 'data mining'],
        'responses': [
            "🌐 **Data Scrapers:**\n\nProfessional data collection from protected sites:\n\n**Standard ($250):**\n• Target Sites: 1 Source\n• Speed: Standard\n• Export: CSV/Excel/JSON\n• Alerts: Email\n• Proxy Support: Basic\n\n**Enterprise ($750):**\n• Target Sites: Up to 5\n• Speed: Real-time\n• Export: API + Webhooks\n• Alerts: Telegram Instant\n• Proxy Support: Advanced\n• Anti-Detect Technology\n\nPerfect for: price monitoring, competitor analysis, data collection."
        ]
    },
    'community': {
        'keywords': ['community', 'group', 'telegram group', 'channel', 'monetization'],
        'responses': [
            "👥 **Community Tools:**\n\nComplete automation for community management:\n\n**Standard ($190):**\n• Anti-Spam: AI Filtering\n• Welcome Msg: Text + Media\n• Payments: Manual Verify\n• Max Users: 10,000\n• Analytics: Basic\n\n**Enterprise ($590):**\n• Anti-Spam: Advanced AI\n• Welcome: Custom Media\n• Payments: Auto USDT/TON\n• Max Users: Unlimited\n• Analytics: Advanced\n• Auto-Kick: Non-Payers\n\nPerfect for: channel monetization, group management, content protection."
        ]
    }
}

# --- БАЗА ЗНАНИЙ БОТА (РУССКАЯ) ---
KNOWLEDGE_BASE_RU = {
    'hello': {
        'keywords': ['привет', 'здравствуйте', 'хай', 'добрый день', 'начать'],
        'responses': [
            "🟦 **NOVA SYSTEMS**\n\nПриветствую! Я профессиональная система автоматизации для Telegram бизнеса.\n\nЧто вас интересует сегодня?",
            "👋 **Добро пожаловать в NOVA SYSTEMS**\n\nЯ специализируюсь на премиальных решениях автоматизации для бизнеса.\n\nЧем могу помочь?"
        ]
    },
    'price': {
        'keywords': ['цена', 'стоимость', 'сколько стоит', 'прайс', 'стоит'],
        'responses': [
            "💰 **Наши цены:**\n\n• AI агенты: $290 (Standard) / $890 (Enterprise)\n• Скраперы: $250 (Standard) / $750 (Enterprise)\n• Инструменты сообществ: $190 (Standard) / $590 (Enterprise)\n\n**Преимущества:**\n- Единоразовый платеж\n- Пожизненная лицензия\n- Полный исходный код\n- 30 дней поддержки\n\nКакое решение вам подходит?"
        ]
    },
    'delivery': {
        'keywords': ['доставка', 'когда получу', 'срок', 'время', 'получить'],
        'responses': [
            "⚡ **Процесс доставки:**\n\n1. **Подтверждение оплаты** (Мгновенно с криптой)\n2. **Настройка системы** (2-4 часа)\n3. **Тестирование** (Ваше подтверждение)\n4. **Финал** (Исходный код + документация)\n\n⏱️ **Сроки доставки:**\n• Standard версии: 1 рабочий день\n• Enterprise версии: 1-3 рабочих дня\n\nДоставляем через зашифрованный Telegram канал."
        ]
    },
    'payment': {
        'keywords': ['оплата', 'платеж', 'крипта', 'usdt', 'ton', 'биткоин'],
        'responses': [
            "💳 **Система оплаты:**\n\nПринимаем **только криптовалюту**:\n✓ Скорость: Подтверждение за секунды\n✓ Приватность: Без личных данных\n✓ Глобально: По всему миру\n✓ Низкие комиссии: Экономия 3-5%\n✓ Безопасность: Без отмен платежей\n\n✅ **Принимаем:** USDT (TRC20/ERC20), TON, Bitcoin, Ethereum\n\nБыстрая доставка, лучшая приватность."
        ]
    },
    'features': {
        'keywords': ['возможности', 'функции', 'что может', 'умеет'],
        'responses': [
            "🚀 **Возможности NOVA SYSTEMS:**\n\n🤖 **Автоматизированные агенты:**\n• Поддержка клиентов 24/7\n• Мультиязычные диалоги\n• Контекстные ответы\n• Интеграция с 50+ платформами\n• 1000+ одновременных чатов\n\n🌐 **Скраперы данных:**\n• Мониторинг в реальном времени\n• Анти-детект технологии\n• Уведомления в Telegram\n• Экспорт в любые форматы\n\n👥 **Инструменты сообществ:**\n• Автоматическое управление подписками\n• Обработка платежей\n• Защита от спама\n• Аналитика пользователей\n• Защита контента"
        ]
    },
    'custom': {
        'keywords': ['кастом', 'настроить', 'индивидуальный', 'особый', 'под меня'],
        'responses': [
            "🎨 **Кастомизация Enterprise:**\n\nEnterprise версии полностью настраиваются:\n\n✓ **Индивидуальные ответы:** Обучаем на ваших данных\n✓ **Интеграция бренда:** Ваш стиль и голос\n✓ **Особые функции:** Уникальный функционал\n✓ **Модификации API:** Под ваши системы\n✓ **Приоритетная разработка:** Ваши запросы в первую очередь\n\nРаботаем напрямую для идеального соответствия."
        ]
    },
    'tech': {
        'keywords': ['технические', 'требования', 'сервер', 'vps', 'хостинг'],
        'responses': [
            "🖥️ **Технические требования:**\n\n**Минимальные (Standard):**\n• VPS с 1GB RAM\n• 10GB места\n• Базовые знания Linux\n• Аккаунт Telegram\n\n**Рекомендуемые (Enterprise):**\n• VPS с 2GB+ RAM\n• 20GB SSD\n• Знание Docker (опционально)\n• Собственный домен\n\n**Мы предоставляем:**\n✓ Скрипты установки\n✓ Файлы конфигурации\n✓ Настройку базы данных\n✓ Помощь с SSL сертификатами"
        ]
    },
    'support': {
        'keywords': ['поддержка', 'помощь', 'обновление', 'обновления'],
        'responses': [
            "🛡️ **Поддержка и обновления:**\n\n**Включено на 30 дней:**\n✓ Помощь с установкой\n✓ Помощь с настройкой\n✓ Исправление ошибок\n✓ Решение проблем\n\n**Пожизненно:**\n✓ Обновления безопасности\n✓ Критические исправления\n✓ Доступ к сообществу\n✓ Обновления документации\n\n**Enterprise добавляет:**\n✓ Приоритетная поддержка 24/7\n✓ Прямой доступ к разработчикам"
        ]
    },
    'why': {
        'keywords': ['почему вы', 'отличие', 'уникальный', 'лучше', 'преимущество'],
        'responses': [
            "🏆 **Почему выбирают нас:**\n\n1. **Проверенные решения:** Используются бизнесами\n2. **Без подписок:** Один платеж, пожизненное использование\n3. **Полная прозрачность:** Исходный код предоставляется\n4. **Качество Enterprise:** Код для масштабирования\n5. **Прямой доступ:** Работа с разработчиками\n6. **Крипто-нативно:** Для современной экономики"
        ]
    },
    'guarantee': {
        'keywords': ['гарантия', 'работает', 'надежность', 'возврат'],
        'responses': [
            "✅ **Наша гарантия:** 30 дней поддержки. Если не работает как описано - исправим.\n\n**Пожизненно:**\n✓ Обновления безопасности\n✓ Критические исправления\n✓ Доступ к сообществу\n\nМы отвечаем за свой код."
        ]
    },
    'ai_agents': {
        'keywords': ['ai агенты', 'чат бот', 'бот поддержки', 'продающий бот'],
        'responses': [
            "🤖 **Автоматизированные агенты:**\n\nПолные системы работы 24/7:\n\n**Standard ($290):**\n• Умные ответы\n• Панель администратора (базовая)\n• Контекстная память (24 часа)\n• Языки: EN & RU\n• Интеграция: Telegram + Сайт\n\n**Enterprise ($890):**\n• Продвинутые ответы\n• Полная панель управления\n• Неограниченная память\n• Мультиязычность\n• Полная кастомизация\n• Все платформы + API\n\nИдеально для: поддержки клиентов, продаж, сбора лидов."
        ]
    },
    'scrapers': {
        'keywords': ['скрапер', 'парсинг', 'сбор данных', 'мониторинг'],
        'responses': [
            "🌐 **Скраперы данных:**\n\nПрофессиональный сбор данных:\n\n**Standard ($250):**\n• Источники: 1 сайт\n• Скорость: Стандартная\n• Экспорт: CSV/Excel/JSON\n• Оповещения: Email\n• Поддержка прокси: Базовая\n\n**Enterprise ($750):**\n• Источники: До 5 сайтов\n• Скорость: Реальное время\n• Экспорт: API + Webhooks\n• Оповещения: Telegram мгновенно\n• Поддержка прокси: Продвинутая\n• Анти-детект технология\n\nИдеально для: мониторинга цен, анализа конкурентов."
        ]
    },
    'community': {
        'keywords': ['сообщество', 'группа', 'канал', 'монетизация', 'паблик'],
        'responses': [
            "👥 **Инструменты сообществ:**\n\nПолная автоматизация управления:\n\n**Standard ($190):**\n• Анти-спам: AI фильтрация\n• Приветствие: Текст + Медиа\n• Платежи: Ручная проверка\n• Макс пользователей: 10,000\n• Аналитика: Базовая\n\n**Enterprise ($590):**\n• Анти-спам: Продвинутый AI\n• Приветствие: Кастомные медиа\n• Платежи: Авто USDT/TON\n• Макс пользователей: Без ограничений\n• Аналитика: Продвинутая\n• Авто-кик: Неплательщики\n\nИдеально для: монетизации каналов, управления группами."
        ]
    }
}

# Запасные ответы
FALLBACK_RESPONSES_EN = [
    "I specialize in professional business automation. Could you rephrase your question about our solutions, pricing, or delivery?",
    "Our expertise lies in building automation systems. Perhaps you'd like to know about pricing, delivery timelines, or technical specifications?",
    "For Enterprise versions, we offer complete customization to match your exact business needs. Let me tell you how we tailor our solutions."
]

FALLBACK_RESPONSES_RU = [
    "Я специализируюсь на профессиональной автоматизации бизнеса. Можете переформулировать вопрос о наших решениях, ценах или доставке?",
    "Мы создаем системы автоматизации. Возможно, вас интересуют цены, сроки доставки или технические детали?",
    "Для Enterprise версий мы предлагаем полную кастомизацию под ваш бизнес. Рассказать, как мы адаптируем решения под конкретные задачи?"
]

def detect_language(text):
    """Определение языка сообщения"""
    if not text:
        return 'en'
    
    ru_chars = sum(1 for char in text.lower() if 'а' <= char <= 'я' or char == 'ё')
    return 'ru' if ru_chars > len(text) / 4 else 'en'

def get_intent(text, language):
    """Определение намерения пользователя"""
    text_lower = text.lower()
    
    # Выбираем соответствующую базу знаний
    knowledge_base = KNOWLEDGE_BASE_RU if language == 'ru' else KNOWLEDGE_BASE_EN
    
    best_intent = None
    best_score = 0
    
    for intent, data in knowledge_base.items():
        for keyword in data['keywords']:
            if keyword in text_lower:
                score = len(keyword) * 2
                if score > best_score:
                    best_score = score
                    best_intent = intent
    
    # Частичные совпадения
    if not best_intent:
        for intent, data in knowledge_base.items():
            for keyword in data['keywords']:
                score = SequenceMatcher(None, text_lower, keyword).ratio()
                if score > 0.7 and score > best_score:
                    best_score = score
                    best_intent = intent
    
    return best_intent if best_score > 0.7 else None

# --- КЛАВИАТУРЫ ---
def get_main_keyboard(language='en'):
    """Основная клавиатура"""
    if language == 'ru':
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="⚡ OPEN NOVA SYSTEM", web_app=WebAppInfo(url=WEBAPP_URL))],
                [KeyboardButton(text="💰 Цены"), KeyboardButton(text="🚀 Доставка")],
                [KeyboardButton(text="💳 Оплата"), KeyboardButton(text="🔧 Поддержка")]
            ],
            resize_keyboard=True,
            input_field_placeholder="Выберите действие..."
        )
    else:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="⚡ OPEN NOVA SYSTEM", web_app=WebAppInfo(url=WEBAPP_URL))],
                [KeyboardButton(text="💰 Prices"), KeyboardButton(text="🚀 Delivery")],
                [KeyboardButton(text="💳 Payment"), KeyboardButton(text="🔧 Support")]
            ],
            resize_keyboard=True,
            input_field_placeholder="Choose action or type question..."
        )

def get_products_keyboard(language='en'):
    """Клавиатура с продуктами"""
    if language == 'ru':
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🤖 AI Agents", callback_data="product_ai")],
                [InlineKeyboardButton(text="🌐 Data Scrapers", callback_data="product_scraper")],
                [InlineKeyboardButton(text="👥 Community Tools", callback_data="product_comm")],
                [InlineKeyboardButton(text="💰 Все цены", callback_data="all_prices")]
            ]
        )
    else:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🤖 AI Agents", callback_data="product_ai")],
                [InlineKeyboardButton(text="🌐 Data Scrapers", callback_data="product_scraper")],
                [InlineKeyboardButton(text="👥 Community Tools", callback_data="product_comm")],
                [InlineKeyboardButton(text="💰 All Prices", callback_data="all_prices")]
            ]
        )

async def recover_messages():
    """Восстановление непрочитанных сообщений после перезапуска"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, message 
            FROM messages 
            WHERE timestamp > datetime('now', '-24 hours')
            ORDER BY timestamp DESC
            LIMIT 100
        ''')
        recent_messages = cursor.fetchall()
        conn.close()
        
        if recent_messages and ADMIN_ID:
            message_text = "🔄 **Bot restarted - Recent messages recovered:**\n\n"
            for user_id, username, message in recent_messages[:10]:  # Первые 10
                if message:
                    message_text += f"👤 @{username if username else 'no_username'} ({user_id}): {message[:50]}...\n"
            
            if len(recent_messages) > 10:
                message_text += f"\n... and {len(recent_messages) - 10} more messages"
            
            await bot.send_message(ADMIN_ID, message_text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error recovering messages: {e}")

async def process_pending_orders():
    """Обработка ожидающих заказов после перезапуска"""
    try:
        pending_orders = await get_pending_orders()
        
        if pending_orders and ADMIN_ID:
            for order_id, user_id, username, cart_data, total, delivery_time in pending_orders:
                try:
                    cart = json.loads(cart_data) if cart_data else []
                    cart_text = "\n".join([f"• {item.get('name', 'Item')} - ${item.get('price', 0)}" for item in cart]) if cart else "No items"
                    
                    # Отправляем уведомление администратору
                    await bot.send_message(
                        ADMIN_ID,
                        f"🔄 **Pending order recovered (ID: {order_id}):**\n\n"
                        f"User: @{username or 'no_username'} ({user_id})\n"
                        f"Total: ${total}\n"
                        f"Delivery: {delivery_time}\n\n"
                        f"**Order:**\n{cart_text}\n\n"
                        f"This order was received while bot was offline.",
                        parse_mode="Markdown"
                    )
                    
                    # Помечаем как обработанный
                    await mark_order_processed(order_id)
                    
                    # Отправляем пользователю уведомление о восстановлении
                    try:
                        await bot.send_message(
                            user_id,
                            "🔄 **System Update:**\n\n"
                            "Our system has been restored after maintenance. "
                            "Your order has been received and is being processed. "
                            "We'll contact you shortly with payment instructions.\n\n"
                            "Thank you for your patience!",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        logging.error(f"Could not notify user {user_id}: {e}")
                        
                except Exception as e:
                    logging.error(f"Error processing recovered order {order_id}: {e}")
    except Exception as e:
        logging.error(f"Error processing pending orders: {e}")

# --- HANDLERS ---

@dp.message(Command("start"))
async def start(message: types.Message):
    # Определяем язык по имени пользователя или первому сообщению
    language = 'ru' if detect_language(message.from_user.first_name or '') == 'ru' else 'en'
    
    welcome_text_en = (
        "🟦 **NOVA SYSTEMS**\n\n"
        "Professional Telegram automation solutions.\n\n"
        "We build systems that:\n"
        "• Work 24/7 without interruptions\n"
        "• Scale to millions of users\n"
        "• Are ready for production use\n\n"
        "Focus on US/EU markets\n\n"
        "👇 **Initialize system:**"
    )
    
    welcome_text_ru = (
        "🟦 **NOVA SYSTEMS**\n\n"
        "Профессиональные решения для автоматизации Telegram.\n\n"
        "Мы создаем системы, которые:\n"
        "• Работают 24/7 без перерывов\n"
        "• Масштабируются на миллионы пользователей\n"
        "• Готовы к промышленному использованию\n\n"
        "Фокус на рынках US/EU\n\n"
        "👇 **Инициализируйте систему:**"
    )
    
    welcome_text = welcome_text_ru if language == 'ru' else welcome_text_en
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard(language),
        parse_mode="Markdown"
    )
    
    # Сохраняем сессию
    await save_session(message.from_user.id, "start", language)
    
    # Уведомление администратору
    if ADMIN_ID:
        await bot.send_message(
            ADMIN_ID,
            f"👤 New user:\n"
            f"ID: {message.from_user.id}\n"
            f"Username: @{message.from_user.username}\n"
            f"Name: {message.from_user.full_name}\n"
            f"Language: {language}"
        )

@dp.message(F.text == "💰 Prices")
@dp.message(F.text == "💰 Цены")
async def show_prices(message: types.Message):
    language = detect_language(message.text)
    
    if language == 'ru':
        response = (
            "💰 **Наши цены:**\n\n"
            "🤖 **Автоматизированные агенты:**\n"
            "• Standard: $290\n"
            "• Enterprise: $890\n\n"
            "🌐 **Data Scrapers:**\n"
            "• Standard: $250\n"
            "• Enterprise: $750\n\n"
            "👥 **Инструменты сообществ:**\n"
            "• Standard: $190\n"
            "• Enterprise: $590\n\n"
            "🎯 **Все лицензии:**\n"
            "- Единоразовый платеж\n"
            "- Пожизненное использование\n"
            "- Полный исходный код\n"
            "- 30 дней поддержки\n\n"
            "Выберите продукт:"
        )
    else:
        response = (
            "💰 **Our pricing:**\n\n"
            "🤖 **Automated Agents:**\n"
            "• Standard: $290\n"
            "• Enterprise: $890\n\n"
            "🌐 **Data Scrapers:**\n"
            "• Standard: $250\n"
            "• Enterprise: $750\n\n"
            "👥 **Community Tools:**\n"
            "• Standard: $190\n"
            "• Enterprise: $590\n\n"
            "🎯 **All licenses include:**\n"
            "- One-time payment\n"
            "- Lifetime use\n"
            "- Full source code\n"
            "- 30-day support\n\n"
            "Choose a product:"
        )
    
    await message.answer(
        response,
        reply_markup=get_products_keyboard(language),
        parse_mode="Markdown"
    )

@dp.message(F.text == "🚀 Delivery")
@dp.message(F.text == "🚀 Доставка")
async def show_delivery(message: types.Message):
    language = detect_language(message.text)
    
    if language == 'ru':
        response = (
            "⚡ **Процесс доставки:**\n\n"
            "1. **Оплата криптой** → Мгновенное подтверждение\n"
            "2. **Настройка системы** → 2-4 часа\n"
            "3. **Тестирование** → Ваше подтверждение\n"
            "4. **Финал** → Полный пакет\n\n"
            "⏱️ **Сроки доставки:**\n"
            "• Standard версии: 1 рабочий день\n"
            "• Enterprise версии: 1-3 рабочих дня\n\n"
            "📦 **Что входит:**\n"
            "✓ Полный исходный код\n"
            "✓ Инструкция по установке\n"
            "✓ Файлы конфигурации\n"
            "✓ Помощь в настройке (1 час)\n"
            "✓ Доступ к приватной поддержке"
        )
    else:
        response = (
            "⚡ **Delivery process:**\n\n"
            "1. **Crypto payment** → Instant confirmation\n"
            "2. **System setup** → 2-4 hours\n"
            "3. **Testing** → Your approval\n"
            "4. **Final** → Complete package\n\n"
            "⏱️ **Delivery timeline:**\n"
            "• Standard versions: 1 business day\n"
            "• Enterprise versions: 1-3 business days\n\n"
            "📦 **Includes:**\n"
            "✓ Full source code\n"
            "✓ Installation guide\n"
            "✓ Configuration files\n"
            "✓ Setup assistance (1 hour)\n"
            "✓ Private support access"
        )
    
    await message.answer(response, parse_mode="Markdown")

@dp.message(F.text == "💳 Payment")
@dp.message(F.text == "💳 Оплата")
async def show_payment(message: types.Message):
    language = detect_language(message.text)
    
    if language == 'ru':
        response = (
            "💳 **Система оплаты:**\n\n"
            "Принимаем только криптовалюту:\n\n"
            "✅ **Почему крипта:**\n"
            "• Мгновенное подтверждение\n"
            "• Без личных данных\n"
            "• Доступно по всему миру\n"
            "• Низкие комиссии (экономия 3-5%)\n"
            "• Без риска отмены платежей\n\n"
            "💰 **Принимаем:**\n"
            "• USDT (TRC20/ERC20)\n"
            "• TON\n"
            "• Bitcoin\n"
            "• Ethereum\n\n"
            f"**Наш кошелек:**\n"
            f"`{USDT_WALLET}`\n\n"
            "После оплаты отправьте хеш транзакции."
        )
    else:
        response = (
            "💳 **Payment system:**\n\n"
            "We accept cryptocurrency only:\n\n"
            "✅ **Why crypto:**\n"
            "• Instant confirmation\n"
            "• No personal data\n"
            "• Available worldwide\n"
            "• Lower fees (save 3-5%)\n"
            "• No chargeback risk\n\n"
            "💰 **Accepted:**\n"
            "• USDT (TRC20/ERC20)\n"
            "• TON\n"
            "• Bitcoin\n"
            "• Ethereum\n\n"
            f"**Our wallet:**\n"
            f"`{USDT_WALLET}`\n\n"
            "Send transaction hash after payment."
        )
    
    await message.answer(response, parse_mode="Markdown")

@dp.message(F.text == "🔧 Support")
@dp.message(F.text == "🔧 Поддержка")
async def show_support(message: types.Message):
    language = detect_language(message.text)
    
    if language == 'ru':
        response = (
            "🛡️ **Поддержка NOVA SYSTEMS:**\n\n"
            "**Включено в покупку:**\n"
            "✓ 30 дней технической поддержки\n"
            "✓ Помощь с установкой и настройкой\n"
            "✓ Исправление проблем\n"
            "✓ Ответы на вопросы\n\n"
            "**Пожизненные преимущества:**\n"
            "✓ Обновления безопасности\n"
            "✓ Критические исправления\n"
            "✓ Доступ к сообществу\n"
            "✓ Обновления документации\n\n"
            "**Enterprise добавляет:**\n"
            "✓ Приоритетная поддержка 24/7\n"
            "✓ Прямой доступ к разработчикам\n"
            "✓ Запросы особых функций\n"
            "✓ Ежемесячные проверки"
        )
    else:
        response = (
            "🛡️ **NOVA SYSTEMS Support:**\n\n"
            "**Included with purchase:**\n"
            "✓ 30 days technical support\n"
            "✓ Installation and setup help\n"
            "✓ Problem resolution\n"
            "✓ Answers to questions\n\n"
            "**Lifetime benefits:**\n"
            "✓ Security updates\n"
            "✓ Critical bug fixes\n"
            "✓ Community access\n"
            "✓ Documentation updates\n\n"
            "**Enterprise adds:**\n"
            "✓ Priority 24/7 support\n"
            "✓ Direct developer access\n"
            "✓ Custom feature requests\n"
            "✓ Monthly check-ins"
        )
    
    await message.answer(response, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("product_"))
async def handle_product_query(callback: types.CallbackQuery):
    product_type = callback.data.split("_")[1]
    language = detect_language(callback.message.text or '')
    
    if product_type == "ai":
        if language == 'ru':
            response = (
                "🤖 **Автоматизированные агенты NOVA:**\n\n"
                "Системы работающие 24/7:\n\n"
                "**Standard ($290):**\n"
                "• Умные ответы\n"
                "• Панель администратора\n"
                "• Контекстная память (24 часа)\n"
                "• Языки: EN & RU\n"
                "• Интеграция: Telegram + Сайт\n\n"
                "**Enterprise ($890):**\n"
                "• Продвинутые ответы\n"
                "• Полная панель управления\n"
                "• Неограниченная память\n"
                "• Мультиязычность\n"
                "• Полная кастомизация\n"
                "• Все платформы + API"
            )
        else:
            response = (
                "🤖 **Automated Agents NOVA:**\n\n"
                "Systems working 24/7:\n\n"
                "**Standard ($290):**\n"
                "• Smart Auto-Reply\n"
                "• Admin Panel\n"
                "• Context Memory (24 hours)\n"
                "• Languages: EN & RU\n"
                "• Integration: Telegram + Web\n\n"
                "**Enterprise ($890):**\n"
                "• Advanced Responses\n"
                "• Full Dashboard\n"
                "• Unlimited Memory\n"
                "• Multi-Language\n"
                "• Full Customization\n"
                "• All Platforms + API"
            )
    elif product_type == "scraper":
        if language == 'ru':
            response = (
                "🌐 **Data Scrapers NOVA:**\n\n"
                "Сбор данных с защищенных сайтов:\n\n"
                "**Standard ($250):**\n"
                "• Источники: 1 сайт\n"
                "• Скорость: Стандартная\n"
                "• Экспорт: CSV/Excel/JSON\n"
                "• Оповещения: Email\n"
                "• Прокси: Базовая поддержка\n\n"
                "**Enterprise ($750):**\n"
                "• Источники: До 5 сайтов\n"
                "• Скорость: Реальное время\n"
                "• Экспорт: API + Webhooks\n"
                "• Оповещения: Telegram мгновенно\n"
                "• Прокси: Продвинутая поддержка\n"
                "• Анти-детект технология"
            )
        else:
            response = (
                "🌐 **Data Scrapers NOVA:**\n\n"
                "Data collection from protected sites:\n\n"
                "**Standard ($250):**\n"
                "• Sources: 1 site\n"
                "• Speed: Standard\n"
                "• Export: CSV/Excel/JSON\n"
                "• Alerts: Email\n"
                "• Proxy: Basic support\n\n"
                "**Enterprise ($750):**\n"
                "• Sources: Up to 5 sites\n"
                "• Speed: Real-time\n"
                "• Export: API + Webhooks\n"
                "• Alerts: Telegram instant\n"
                "• Proxy: Advanced support\n"
                "• Anti-Detect Technology"
            )
    elif product_type == "comm":
        if language == 'ru':
            response = (
                "👥 **Инструменты сообществ NOVA:**\n\n"
                "Автоматизация управления сообществами:\n\n"
                "**Standard ($190):**\n"
                "• Анти-спам: AI фильтрация\n"
                "• Приветствие: Текст + Медиа\n"
                "• Платежи: Ручная проверка\n"
                "• Пользователи: До 10,000\n"
                "• Аналитика: Базовая\n\n"
                "**Enterprise ($590):**\n"
                "• Анти-спам: Продвинутый AI\n"
                "• Приветствие: Кастомные медиа\n"
                "• Платежи: Авто USDT/TON\n"
                "• Пользователи: Без ограничений\n"
                "• Аналитика: Продвинутая\n"
                "• Авто-кик: Неплательщики"
            )
        else:
            response = (
                "👥 **Community Tools NOVA:**\n\n"
                "Community management automation:\n\n"
                "**Standard ($190):**\n"
                "• Anti-Spam: AI Filtering\n"
                "• Welcome: Text + Media\n"
                "• Payments: Manual Verify\n"
                "• Users: Up to 10,000\n"
                "• Analytics: Basic\n\n"
                "**Enterprise ($590):**\n"
                "• Anti-Spam: Advanced AI\n"
                "• Welcome: Custom Media\n"
                "• Payments: Auto USDT/TON\n"
                "• Users: Unlimited\n"
                "• Analytics: Advanced\n"
                "• Auto-Kick: Non-Payers"
            )
    elif product_type == "all_prices":
        if language == 'ru':
            response = (
                "💰 **Все цены:**\n\n"
                "🤖 AI Agents: $290 / $890\n"
                "🌐 Data Scrapers: $250 / $750\n"
                "👥 Community Tools: $190 / $590\n\n"
                "**Все версии включают:**\n"
                "- Единоразовый платеж\n"
                "- Пожизненная лицензия\n"
                "- Полный исходный код\n"
                "- 30 дней поддержки"
            )
        else:
            response = (
                "💰 **All Prices:**\n\n"
                "🤖 AI Agents: $290 / $890\n"
                "🌐 Data Scrapers: $250 / $750\n"
                "👥 Community Tools: $190 / $590\n\n"
                "**All versions include:**\n"
                "- One-time payment\n"
                "- Lifetime license\n"
                "- Full source code\n"
                "- 30-day support"
            )
    
    await callback.message.answer(response, parse_mode="Markdown")
    await callback.answer()

@dp.message(F.content_type == "web_app_data")
async def handle_web_app_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        user_id = message.from_user.id
        username = message.from_user.username or str(user_id)
        language = detect_language(message.text or 'en')
        
        if data['type'] == 'contact':
            await message.answer(
                "👨‍💻 **Developer channel activated**\n\n"
                "I've forwarded your request directly to the developer. "
                "They will contact you shortly.\n\n"
                "In the meantime, feel free to ask any technical questions.",
                reply_markup=get_main_keyboard(language)
            )
            
            # Сохраняем в базу
            await save_message(user_id, username, "Requested contact", "Forwarded to developer", language)
            
            if ADMIN_ID:
                await bot.send_message(
                    ADMIN_ID,
                    f"📞 **CONTACT REQUEST**\n"
                    f"User requested contact with developer\n"
                    f"ID: {user_id}\n"
                    f"Username: @{username}\n"
                    f"Name: {message.from_user.full_name}\n"
                    f"Language: {language}"
                )
            return

        if data['type'] == 'order':
            cart_items = data.get('cart', [])
            total = data.get('total', 0)
            
            cart_text = "\n".join([f"• {item.get('name', 'Item')} - ${item.get('price', 0)}" for item in cart_items])
            
            # Определяем срок доставки
            has_pro = any(item.get('tier') == 'pro' for item in cart_items)
            if language == 'ru':
                delivery_time = "1-3 рабочих дня" if has_pro else "1 рабочий день"
            else:
                delivery_time = "1-3 business days" if has_pro else "1 business day"
            
            # Сохраняем заказ в базу
            order_id = await save_order(user_id, username, json.dumps(cart_items), total, delivery_time)
            
            if language == 'ru':
                response = (
                    f"✅ **ЗАКАЗ СОЗДАН**\n\n"
                    f"📦 **Ваш заказ (ID: {order_id}):**\n"
                    f"{cart_text}\n"
                    f"──────────────\n"
                    f"💎 **Итого: ${total}**\n\n"
                    f"🚀 **Доставка:** {delivery_time}\n\n"
                    f"💳 **Оплата криптовалютой:**\n"
                    f"Кошелек (TRC20):\n"
                    f"`{USDT_WALLET}`\n\n"
                    f"**Инструкция:**\n"
                    f"1. Отправьте ${total} на указанный кошелек\n"
                    f"2. Пришлите хеш транзакции\n"
                    f"3. Мы активируем доставку в течение часа"
                )
            else:
                response = (
                    f"✅ **ORDER CREATED**\n\n"
                    f"📦 **Your order (ID: {order_id}):**\n"
                    f"{cart_text}\n"
                    f"──────────────\n"
                    f"💎 **Total: ${total}**\n\n"
                    f"🚀 **Delivery:** {delivery_time}\n\n"
                    f"💳 **Crypto payment:**\n"
                    f"Wallet (TRC20):\n"
                    f"`{USDT_WALLET}`\n\n"
                    f"**Instructions:**\n"
                    f"1. Send ${total} to the wallet above\n"
                    f"2. Send transaction hash\n"
                    f"3. We activate delivery within an hour"
                )
            
            await message.answer(response, parse_mode="Markdown")
            
            # Сохраняем в базу
            await save_message(user_id, username, "Created order", f"Order ID: {order_id}, Total: ${total}", language)
            
            # Уведомление администратору
            if ADMIN_ID:
                order_details = "\n".join([f"- {item.get('name', 'Item')} (${item.get('price', 0)})" for item in cart_items]) if cart_items else "No items"
                await bot.send_message(
                    ADMIN_ID,
                    f"💰 **NEW ORDER!**\n\n"
                    f"Order ID: {order_id}\n"
                    f"User: @{username}\n"
                    f"ID: {user_id}\n"
                    f"Total: ${total}\n"
                    f"Delivery: {delivery_time}\n\n"
                    f"**Order:**\n{order_details}"
                )
            
            return

    except Exception as e:
        logging.error(f"Error processing web_app_data: {e}")
        error_msg = "⚠️ An error occurred processing your request. Please try again."
        if detect_language(message.text or '') == 'ru':
            error_msg = "⚠️ Произошла ошибка обработки вашего запроса. Пожалуйста, попробуйте еще раз."
        await message.answer(error_msg)

@dp.message(F.text)
async def handle_text_message(message: types.Message):
    user_text = message.text
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)
    
    # Определяем язык
    language = detect_language(user_text)
    
    # Получаем сессию если есть
    session = await get_session(user_id)
    if session:
        last_context, last_language = session
        # Если язык в сессии отличается, обновляем
        if last_language != language:
            language = last_language
    
    # Определяем намерение
    intent = get_intent(user_text, language)
    
    # Выбираем базу знаний
    knowledge_base = KNOWLEDGE_BASE_RU if language == 'ru' else KNOWLEDGE_BASE_EN
    fallback_responses = FALLBACK_RESPONSES_RU if language == 'ru' else FALLBACK_RESPONSES_EN
    
    if intent and intent in knowledge_base:
        # Выбираем случайный ответ
        responses = knowledge_base[intent]['responses']
        response = responses[hash(f"{user_id}{intent}") % len(responses)]
        
        await message.answer(response, parse_mode="Markdown")
        
        # Сохраняем в базу
        await save_message(user_id, username, user_text, response, language)
        await save_session(user_id, intent, language)
        
        # Если вопрос про оплату - добавляем кошелек
        if intent == 'payment':
            wallet_text = f"**Wallet (TRC20):**\n`{USDT_WALLET}`\n\nSend transaction hash after payment."
            if language == 'ru':
                wallet_text = f"**Кошелек (TRC20):**\n`{USDT_WALLET}`\n\nОтправьте хеш транзакции после оплаты."
            
            await message.answer(wallet_text, parse_mode="Markdown")
            
    else:
        # Не нашли подходящий ответ
        response = fallback_responses[hash(f"{user_id}{user_text}") % len(fallback_responses)]
        await message.answer(response, parse_mode="Markdown")
        
        # Сохраняем в базу
        await save_message(user_id, username, user_text, response, language)
        
        # Отправляем админу для улучшения базы знаний
        if ADMIN_ID:
            lang_label = "RU" if language == 'ru' else "EN"
            await bot.send_message(
                ADMIN_ID,
                f"🤔 **UNPROCESSED QUERY**\n"
                f"From: @{username}\n"
                f"ID: {user_id}\n"
                f"Language: {lang_label}\n"
                f"Message: {user_text}\n\n"
                f"Bot replied: {response}"
            )

@dp.message(F.reply_to_message)
async def handle_admin_reply(message: types.Message):
    """Обработка ответов администратора пользователям"""
    if str(message.from_user.id) != ADMIN_ID:
        return
    
    original_message = message.reply_to_message.text
    
    # Ищем ID пользователя в сообщении
    user_id_match = re.search(r"ID: (\d+)", original_message)
    if user_id_match:
        user_id = int(user_id_match.group(1))
        
        try:
            # Отправляем ответ пользователю
            await bot.send_message(
                user_id,
                f"👨‍💻 **Message from developer:**\n\n{message.text}"
            )
            await message.answer("✅ Reply sent to user.")
            
            # Сохраняем в базу
            username = message.from_user.username or "admin"
            await save_message(user_id, username, f"Admin reply to: {original_message[:50]}", message.text, 'en')
            
        except Exception as e:
            await message.answer(f"❌ Error sending: {e}")

async def main():
    # Инициализируем базу данных
    await init_db()
    
    # Восстанавливаем сообщения и заказы после перезапуска
    await recover_messages()
    await process_pending_orders()
    
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("🟢 NOVA SYSTEMS bot started and ready!")
    logging.info(f"🤖 Token: {TOKEN[:10]}...")
    logging.info(f"👑 Admin: {ADMIN_ID}")
    logging.info(f"💾 Database: {DATABASE}")
    
    if ADMIN_ID:
        await bot.send_message(
            ADMIN_ID, 
            "🟢 **NOVA SYSTEMS bot restarted successfully!**\n\n"
            "✅ Database initialized\n"
            "✅ Messages recovery completed\n"
            "✅ Pending orders processed\n"
            "✅ Ready to receive messages"
        )
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())