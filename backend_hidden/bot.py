import asyncio
import json
import logging
import os
import re
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

# Data directory setup
DATA_DIR = "data"
MESSAGES_FILE = os.path.join(DATA_DIR, "pending_messages.json")
ORDERS_FILE = os.path.join(DATA_DIR, "pending_orders.json")

os.makedirs(DATA_DIR, exist_ok=True)

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# --- DATA STORAGE FUNCTIONS ---
def save_pending_message(user_id: int, username: str, text: str):
    """Сохраняем сообщение в файл для восстановления"""
    try:
        if os.path.exists(MESSAGES_FILE):
            with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                messages = json.load(f)
        else:
            messages = []
        
        messages.append({
            'user_id': user_id,
            'username': username,
            'text': text,
            'timestamp': datetime.now().isoformat(),
            'processed': False
        })
        
        with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        logging.error(f"Error saving message: {e}")

def save_pending_order(order_data: dict):
    """Сохраняем заказ в файл для восстановления"""
    try:
        if os.path.exists(ORDERS_FILE):
            with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
                orders = json.load(f)
        else:
            orders = []
        
        orders.append({
            **order_data,
            'timestamp': datetime.now().isoformat(),
            'processed': False
        })
        
        with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        logging.error(f"Error saving order: {e}")

def mark_message_processed(user_id: int, text: str):
    """Помечаем сообщение как обработанное"""
    try:
        if not os.path.exists(MESSAGES_FILE):
            return
            
        with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
            messages = json.load(f)
        
        # Ищем и помечаем сообщение
        for msg in messages:
            if msg['user_id'] == user_id and msg['text'] == text and not msg['processed']:
                msg['processed'] = True
                
        with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        logging.error(f"Error marking message as processed: {e}")

def mark_order_processed(order_data: dict):
    """Помечаем заказ как обработанный"""
    try:
        if not os.path.exists(ORDERS_FILE):
            return
            
        with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
            orders = json.load(f)
        
        # Ищем и помечаем заказ
        for order in orders:
            if (order.get('total') == order_data.get('total') and 
                order.get('cart') == order_data.get('cart') and 
                not order.get('processed', True)):
                order['processed'] = True
                
        with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        logging.error(f"Error marking order as processed: {e}")

async def restore_pending_data():
    """Восстанавливаем непрочитанные сообщения и заказы при перезапуске"""
    try:
        # Восстанавливаем сообщения
        if os.path.exists(MESSAGES_FILE):
            with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                messages = json.load(f)
            
            pending_messages = [msg for msg in messages if not msg['processed']]
            if pending_messages and ADMIN_ID:
                for msg in pending_messages:
                    await bot.send_message(
                        ADMIN_ID,
                        f"📩 **MESSAGE RESTORED**\n\n"
                        f"From: @{msg['username']} [ID: {msg['user_id']}]\n"
                        f"Time: {msg['timestamp']}\n"
                        f"Message: {msg['text']}\n\n"
                        f"(Received while offline)"
                    )
                    msg['processed'] = True # Mark as processed
                
                # Save changes
                with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
                    json.dump(messages, f, ensure_ascii=False, indent=2)
                    
                logging.info(f"Restored {len(pending_messages)} pending messages")
        
        # Восстанавливаем заказы
        if os.path.exists(ORDERS_FILE):
            with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
                orders = json.load(f)
            
            pending_orders = [order for order in orders if not order['processed']]
            if pending_orders and ADMIN_ID:
                for order in pending_orders:
                    cart_text = "\n".join([f"• {item['name']} - ${item['price']}" for item in order['cart']])
                    await bot.send_message(
                        ADMIN_ID,
                        f"💰 **ORDER RESTORED**\n\n"
                        f"User: @{order.get('username', 'Unknown')}\n"
                        f"Time: {order['timestamp']}\n"
                        f"Total: ${order['total']}\n\n"
                        f"Items:\n{cart_text}\n\n"
                        f"(Received while offline)"
                    )
                    order['processed'] = True # Mark as processed

                # Save changes
                with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(orders, f, ensure_ascii=False, indent=2)

                logging.info(f"Restored {len(pending_orders)} pending orders")
                
    except Exception as e:
        logging.error(f"Error restoring pending data: {e}")

# --- PRODUCTS DATA ---
PRODUCTS = {
    'ai': {
        'core': {'price': 290, 'name': "AI Support Core", 'category': 'AI Agents'},
        'pro': {'price': 890, 'name': "AI Sales Agent PRO", 'category': 'AI Agents'}
    },
    'scraper': {
        'core': {'price': 250, 'name': "Scraper Basic", 'category': 'Data Scrapers'},
        'pro': {'price': 750, 'name': "Data Miner PRO", 'category': 'Data Scrapers'}
    },
    'comm': {
        'core': {'price': 190, 'name': "Group Manager", 'category': 'Community Tools'},
        'pro': {'price': 590, 'name': "Subscription Empire", 'category': 'Community Tools'}
    }
}

# --- KNOWLEDGE BASE (ENGLISH PRIMARY, RUSSIAN SECONDARY) ---
KNOWLEDGE_BASE = {
    'hello': {
        'keywords_en': ['hello', 'hi', 'hey', 'start', 'good morning', 'wazzap', 'sup'],
        'keywords_ru': ['привет', 'здравствуйте', 'хай', 'добрый день', 'начать'],
        'responses_en': [
            "🤖 **NOVA SYSTEMS**\n\nWelcome! I'm NOVA - professional automation system for Telegram business.\n\nWe create solutions that work 24/7, scale without limits, and deliver immediate value.\n\nWhat are you interested in today?",
            "👋 **Welcome to NOVA SYSTEMS**\n\nI specialize in premium automation solutions for serious businesses. What can I help you with?"
        ],
        'responses_ru': [
            "🤖 **NOVA SYSTEMS**\n\nДобро пожаловать! Я NOVA - профессиональная система автоматизации для Telegram бизнеса.\n\nМы создаем решения, которые работают 24/7, масштабируются без ограничений и приносят пользу сразу.\n\nЧто вас интересует сегодня?",
            "👋 **Добро пожаловать в NOVA SYSTEMS**\n\nЯ специализируюсь на премиальных решениях автоматизации для серьезного бизнеса. Чем могу помочь?"
        ]
    },
    'price': {
        'keywords_en': ['price', 'cost', 'how much', 'money', 'expensive', 'cheap', 'pricing'],
        'keywords_ru': ['сколько стоит', 'цена', 'стоимость', 'прайс', 'стоит'],
        'responses_en': [
            "💰 **NOVA Investment Structure:**\n\n• AI Agents: $290 (Standard) / $890 (Enterprise)\n• Data Scrapers: $250 (Standard) / $750 (Enterprise)\n• Community Tools: $190 (Standard) / $590 (Enterprise)\n\n🎯 **Key Benefits:**\n- One-time payment (no subscriptions)\n- Lifetime license\n- Complete source code\n- 30 days included support\n\nWhich solution fits your business scale?",
            "💎 **Value Proposition:**\n\nOur prices reflect enterprise-level quality. Standard versions cover 90% of needs. Enterprise adds full customization and priority support."
        ],
        'responses_ru': [
            "💰 **Структура инвестиций NOVA:**\n\n• AI агенты: $290 (Standard) / $890 (Enterprise)\n• Скраперы: $250 (Standard) / $750 (Enterprise)\n• Инструменты сообществ: $190 (Standard) / $590 (Enterprise)\n\n🎯 **Ключевые преимущества:**\n- Единоразовый платеж (без подписок)\n- Пожизненная лицензия\n- Полный исходный код\n- 30 дней поддержки включено\n\nКакое решение подходит масштабу вашего бизнеса?",
            "💎 **Предложение ценности:**\n\nНаши цены отражают качество enterprise-уровня. Standard версии покрывают 90% задач. Enterprise добавляет полную кастомизацию и приоритетную поддержку."
        ]
    },
    'delivery': {
        'keywords_en': ['delivery', 'when get', 'timeline', 'receive', 'ship', 'deliver'],
        'keywords_ru': ['доставка', 'когда получу', 'срок', 'получить', 'отправка'],
        'responses_en': [
            "⚡ **Delivery Process:**\n\n1. **Payment Confirmation** (Instant with crypto)\n2. **Setup & Configuration** (2-4 hours)\n3. **Testing** (Your approval required)\n4. **Final Delivery** (Complete package)\n\n⏱️ **Delivery Time:**\n• Standard versions: 1 business day\n• Enterprise versions: 1-3 business days (customization may extend)\n\nWe deliver via encrypted Telegram channel with full documentation.",
            "🚀 **Fast Delivery:**\n\nAverage delivery time is 12-24 hours. We value your time.\n\nWhat's included:\n✓ Complete source code\n✓ Installation guide\n✓ Configuration files\n✓ Setup assistance (1 hour)\n✓ Access to private support channel"
        ],
        'responses_ru': [
            "⚡ **Процесс доставки:**\n\n1. **Подтверждение оплаты** (Мгновенно с криптой)\n2. **Настройка** (2-4 часа)\n3. **Тестирование** (Ваше подтверждение)\n4. **Финал** (Полный пакет)\n\n⏱️ **Сроки доставки:**\n• Standard версии: 1 рабочий день\n• Enterprise версии: 1-3 рабочих дня (кастомизация может увеличить)\n\nДоставляем через зашифрованный Telegram канал с полной документацией.",
            "🚀 **Быстрая доставка:**\n\nСреднее время доставки - 12-24 часа. Мы ценим ваше время.\n\nЧто входит в доставку:\n✓ Полный исходный код\n✓ Инструкция по установке\n✓ Файлы конфигурации\n✓ Помощь в настройке (1 час)\n✓ Доступ к приватному каналу поддержки"
        ]
    },
    'payment': {
        'keywords_en': ['payment', 'pay', 'crypto', 'bitcoin', 'usdt', 'ton', 'ethereum', 'wallet'],
        'keywords_ru': ['оплата', 'крипта', 'биткоин', 'usdt', 'ton', 'кошелек', 'платеж'],
        'responses_en': [
            "💳 **NOVA Payment System:**\n\nWe accept **cryptocurrency only** for several reasons:\n\n✓ **Speed:** Confirmation in seconds (vs 3-5 days with banks)\n✓ **Privacy:** No personal data required\n✓ **Global:** Available worldwide\n✓ **Low fees:** Save 3-5% on payment processing\n✓ **Security:** No chargebacks\n\n✅ **Accepted:** USDT (TRC20/ERC20), TON, Bitcoin, Ethereum\n\nFaster delivery, better privacy.",
            "🔐 **Why Crypto Payments:**\n\n1. **Instant:** Solution within hours, not days\n2. **Private:** Your business stays confidential\n3. **Cost-effective:** Minimal fees\n4. **Secure:** No payment reversal risk\n\n**Payment Wallet:**\n`" + USDT_WALLET + "`\n\nSend transaction hash after payment for instant activation."
        ],
        'responses_ru': [
            "💳 **Платежная система NOVA:**\n\nМы принимаем **только криптовалюту** по нескольким причинам:\n\n✓ **Скорость:** Подтверждение за секунды (против 3-5 дней у банков)\n✓ **Приватность:** Никаких личных данных\n✓ **Глобально:** Работаем по всему миру\n✓ **Низкие комиссии:** Экономите 3-5%\n✓ **Безопасность:** Никаких чарджбэков\n\n✅ **Принимаем:** USDT (TRC20/ERC20), TON, Bitcoin, Ethereum\n\nБыстрее доставка, лучше приватность.",
            "🔐 **Почему крипто-оплата:**\n\n1. **Мгновенно:** Решение через часы, а не дни\n2. **Конфиденциально:** Ваш бизнес остается приватным\n3. **Выгодно:** Минимальные комиссии\n4. **Безопасно:** Нет риска отмены платежей\n\n**Кошелек для оплаты:**\n`" + USDT_WALLET + "`\n\nПосле оплаты отправьте хеш транзакции для мгновенной активации."
        ]
    },
    'features': {
        'keywords_en': ['features', 'what can', 'can do', 'capabilities', 'functions'],
        'keywords_ru': ['возможности', 'функции', 'что может', 'умеет'],
        'responses_en': [
            "🚀 **NOVA SYSTEMS Capabilities:**\n\n🤖 **Automated Agents:**\n• 24/7 customer support\n• Multi-language conversations\n• Context-aware responses\n• Integration with 50+ platforms\n• 1000+ simultaneous chats\n\n🌐 **Data Scrapers:**\n• Real-time monitoring\n• Anti-detection technology\n• Telegram/email alerts\n• 50+ pages per second\n\n👥 **Community Tools:**\n• Automated subscription management\n• Payment processing\n• Anti-spam protection\n• User analytics\n• Content protection",
            "💪 **What You Get:**\n\n• **Efficiency:** Automate repetitive tasks\n• **Scalability:** Handle unlimited growth\n• **Reliability:** 99.9% uptime guarantee\n• **Quality:** Enterprise-grade solutions\n\nEach solution is tested in real business environments."
        ],
        'responses_ru': [
            "🚀 **Возможности NOVA SYSTEMS:**\n\n🤖 **Автоматизированные агенты:**\n• 24/7 поддержка клиентов\n• Мультиязычные диалоги\n• Контекстные ответы\n• Интеграция с 50+ платформами\n• 1000+ одновременных чатов\n\n🌐 **Data Scrapers:**\n• Мониторинг в реальном времени\n• Анти-детект технологии\n• Оповещения в Telegram\n• 50+ страниц в секунду\n\n👥 **Инструменты сообществ:**\n• Автоматическое управление подписками\n• Обработка платежей\n• Защита от спама\n• Аналитика пользователей\n• Защита контента",
            "💪 **Что вы получаете:**\n\n• **Эффективность:** Автоматизируйте рутинные задачи\n• **Масштабируемость:** Поддержка неограниченного роста\n• **Надежность:** Гарантия 99.9% аптайма\n• **Качество:** Решения enterprise-уровня\n\nКаждое решение проверено в реальных бизнес-условиях."
        ]
    },
    'custom': {
        'keywords_en': ['custom', 'customization', 'customize', 'pro', 'enterprise', 'special', 'modify'],
        'keywords_ru': ['кастом', 'настроить', 'индивидуальный', 'особый', 'изменить'],
        'responses_en': [
            "🎨 **Enterprise Version Customization:**\n\nEnterprise versions are fully customizable to your business needs:\n\n✓ **Tailored Responses:** Trained on your specific data\n✓ **Brand Integration:** Your branding, your voice\n✓ **Custom Features:** Add unique functionality\n✓ **API Modifications:** Adjust to your existing systems\n✓ **Priority Development:** Your requests go first\n\nWe work directly with you to ensure perfect fit for your requirements.",
            "🔧 **Personalized Approach:**\n\nWith Enterprise versions, you're not just buying software - you're getting a solution molded to your business. We adjust:\n• Personality and knowledge base\n• Integration points with your CRM\n• Reporting and analytics format\n• Alert systems and notifications\n• User interface and experience"
        ],
        'responses_ru': [
            "🎨 **Кастомизация Enterprise версий:**\n\nEnterprise версии полностью настраиваются под ваш бизнес:\n\n✓ **Индивидуальные ответы:** Обучаем на ваших данных\n✓ **Интеграция бренда:** Ваш стиль, ваш голос\n✓ **Особые функции:** Добавляем уникальный функционал\n✓ **Модификации API:** Настраиваем под ваши системы\n✓ **Приоритетная разработка:** Ваши запросы в первую очередь\n\nРаботаем напрямую, чтобы решение идеально подошло под ваши требования.",
            "🔧 **Индивидуальный подход:**\n\nС Enterprise версиями вы получаете не просто софт, а решение, созданное под ваш бизнес. Мы настраиваем:\n• Личность и базу знаний\n• Точки интеграции с вашей CRM\n• Формат отчетов и аналитики\n• Систему оповещений\n• Интерфейс и опыт пользователей"
        ]
    },
    'tech': {
        'keywords_en': ['technical', 'requirements', 'server', 'vps', 'hosting', 'setup', 'install'],
        'keywords_ru': ['технические', 'требования', 'сервер', 'хостинг', 'установка'],
        'responses_en': [
            "🖥️ **Technical Requirements:**\n\n**Minimal (Standard):**\n• VPS with 1GB RAM\n• 10GB storage\n• Basic Linux knowledge\n• Telegram account\n\n**Recommended (Enterprise):**\n• VPS with 2GB+ RAM\n• 20GB SSD\n• Docker knowledge (optional)\n• Custom domain\n\n**We Provide:**\n✓ Installation scripts\n✓ Configuration files\n✓ Database setup\n✓ SSL certificate guidance\n✓ Monitoring tools",
            "⚙️ **Infrastructure:**\n\nSolutions run on any VPS (DigitalOcean, AWS, Hetzner, etc).\n\n**Setup Time:** 30-60 minutes with our scripts.\n\n**No Coding Required** for standard versions.\n\n**Support:** We help with initial setup and provide maintenance documentation.\n\nEven beginners can have it running within an hour."
        ],
        'responses_ru': [
            "🖥️ **Технические требования:**\n\n**Минимальные (Standard):**\n• VPS с 1GB RAM\n• 10GB места\n• Базовые знания Linux\n• Аккаунт Telegram\n\n**Рекомендуемые (Enterprise):**\n• VPS с 2GB+ RAM\n• 20GB SSD\n• Знание Docker (опционально)\n• Собственный домен\n\n**Мы предоставляем:**\n✓ Скрипты установки\n✓ Файлы конфигурации\n✓ Настройку базы данных\n✓ Помощь с SSL сертификатами\n✓ Инструменты мониторинга",
            "⚙️ **Инфраструктура:**\n\nРешения работают на любом VPS (DigitalOcean, AWS, Hetzner и др).\n\n**Время настройки:** 30-60 минут с нашими скриптами.\n\n**Не нужно знать программирование** для стандартных версий.\n\n**Поддержка:** Помогаем с начальной настройкой, даем документацию для поддержки.\n\nДаже новички запускают решение за час."
        ]
    },
    'support': {
        'keywords_en': ['support', 'help', 'update', 'updates', 'problem', 'issue', 'bug'],
        'keywords_ru': ['поддержка', 'помощь', 'обновление', 'проблема', 'ошибка'],
        'responses_en': [
            "🛡️ **Support & Updates:**\n\n**Included for 30 days:**\n✓ Installation assistance\n✓ Configuration help\n✓ Bug fixes\n✓ Basic troubleshooting\n\n**Lifetime Benefits:**\n✓ Security updates\n✓ Critical bug fixes\n✓ Community access\n✓ Documentation updates\n\n**Enterprise adds:**\n✓ Priority 24/7 support\n✓ Custom feature requests\n✓ Direct developer access\n✓ Monthly check-ins",
            "🤝 **Quality Assurance:**\n\n1. **Initial Setup:** We help you get running\n2. **Learning Period:** 30 days of guided support\n3. **Long-Term:** Lifetime updates for critical issues\n4. **Community:** Access to other successful users\n\nOur goal is your success. We're invested in making sure our solutions work perfectly for you."
        ],
        'responses_ru': [
            "🛡️ **Поддержка и обновления:**\n\n**Включено на 30 дней:**\n✓ Помощь с установкой\n✓ Помощь с настройкой\n✓ Исправление ошибок\n✓ Базовое решение проблем\n\n**Пожизненно:**\n✓ Обновления безопасности\n✓ Исправление критических ошибок\n✓ Доступ к сообществу\n✓ Обновления документации\n\n**Enterprise добавляет:**\n✓ Приоритетная поддержка 24/7\n✓ Запросы особых функций\n✓ Прямой доступ к разработчикам\n✓ Ежемесячные проверки",
            "🤝 **Гарантия качества:**\n\n1. **Начальная настройка:** Помогаем запустить\n2. **Период обучения:** 30 дней поддержки\n3. **Долгосрочно:** Пожизненные обновления\n4. **Сообщество:** Доступ к успешным пользователям\n\nНаша цель - ваш успех. Мы заинтересованы в том, чтобы решения работали идеально."
        ]
    },
    'guarantee': {
        'keywords_en': ['warranty', 'guarantee', 'refund', 'working', 'does it work', 'reliable'],
        'keywords_ru': ['гарантия', 'возврат', 'работает', 'надежно'],
        'responses_en': [
            "✅ **Our Guarantee:** 30 days of included support. If the solution doesn't work as described, we fix it. Lifetime bug fixes. We stand behind our code - it's tested and production-ready.",
            "🔒 **Quality Guarantee:**\n\nYou get working solutions, not just code. 30-day support included. We fix any issues. Our reputation is built on delivering what we promise."
        ],
        'responses_ru': [
            "✅ **Наша гарантия:** 30 дней поддержки включено. Если решение не работает как описано - исправим. Пожизненные исправления ошибок. Мы отвечаем за свой код - он проверен и готов к работе.",
            "🔒 **Гарантия качества:**\n\nВы получаете работающие решения, а не просто код. 30 дней поддержки включено. Исправляем любые проблемы. Наша репутация построена на выполнении обещаний."
        ]
    },
    'ai_agents': {
        'keywords_en': ['ai agent', 'ai agents', 'chat bot', 'support bot', 'sales bot'],
        'keywords_ru': ['ai агент', 'чат бот', 'бот поддержки', 'продающий бот'],
        'responses_en': [
            "🤖 **NOVA Automated Agents:**\n\nThese are not just chat bots. These are complete systems that:\n• Handle sales 24/7\n• Answer customer questions\n• Learn from your data\n• Integrate with your website and Telegram\n• Process thousands of conversations simultaneously\n\nStandard: $290 (basic functionality)\nEnterprise: $890 (full customization)",
            "💬 **Smart Agents for Business:**\n\nOur agents use advanced natural language processing to understand customer queries and provide relevant responses.\n\nThey can:\n• Sell products\n• Consult clients\n• Collect leads\n• Integrate with payment systems"
        ],
        'responses_ru': [
            "🤖 **Автоматизированные агенты NOVA:**\n\nЭто не просто чат-боты. Это полноценные системы, которые:\n• Ведут продажи 24/7\n• Отвечают на вопросы клиентов\n• Обучаются на ваших данных\n• Интегрируются с вашим сайтом и Telegram\n• Обрабатывают тысячи диалогов одновременно\n\nStandard: $290 (базовый функционал)\nEnterprise: $890 (полная кастомизация)",
            "💬 **Умные агенты для бизнеса:**\n\nНаши агенты используют передовые технологии обработки естественного языка для понимания запросов клиентов и предоставления релевантных ответов.\n\nОни могут:\n• Продавать продукты\n• Консультировать клиентов\n• Собирать лиды\n• Интегрироваться с платежными системами"
        ]
    },
    'scrapers': {
        'keywords_en': ['scraper', 'parsing', 'data extraction', 'monitoring', 'data mining'],
        'keywords_ru': ['скрапер', 'парсинг', 'сбор данных', 'мониторинг'],
        'responses_en': [
            "🌐 **NOVA Data Scrapers:**\n\nProfessional data collection systems that:\n• Monitor prices in real-time\n• Bypass anti-bot protection\n• Work with proxy rotation\n• Export data in any format\n• Send instant notifications\n\nPerfect for:\n- Traffic arbitration\n- Competitor monitoring\n- Lead collection\n- Market analysis\n\nStandard: $250 (1 source)\nEnterprise: $750 (up to 5 sources)",
            "📊 **Powerful Scrapers for Business:**\n\nOur data collection solutions use advanced technologies to extract information from any website, including those protected by Cloudflare and with JavaScript rendering."
        ],
        'responses_ru': [
            "🌐 **Data Scrapers от NOVA:**\n\nПрофессиональные системы сбора данных, которые:\n• Мониторят цены в реальном времени\n• Обходят анти-бот защиту\n• Работают с прокси-ротацией\n• Экспортируют данные в любом формате\n• Отправляют мгновенные уведомления\n\nИдеально для:\n- Арбитража трафика\n- Мониторинга конкурентов\n- Сбора лидов\n- Анализа рынка\n\nStandard: $250 (1 источник)\nEnterprise: $750 (до 5 источников)",
            "📊 **Мощные скраперы для бизнеса:**\n\nНаши решения для сбора данных используют передовые технологии для извлечения информации с любых сайтов, включая защищенные Cloudflare и с JavaScript-рендерингом."
        ]
    },
    'community': {
        'keywords_en': ['community', 'telegram group', 'channel', 'monetization', 'subscription'],
        'keywords_ru': ['сообщество', 'группа', 'канал', 'монетизация', 'подписка'],
        'responses_en': [
            "👥 **NOVA Community Tools:**\n\nComplete set for community monetization and management:\n• Automatic payment verification\n• Kick non-payers\n• Welcome messages\n• Anti-spam protection\n• Activity analytics\n• Subscription management\n\nStandard: $190 (basic management)\nEnterprise: $590 (full payment automation)",
            "💰 **Community Monetization:**\n\nTurn your Telegram community into a source of stable income. Our tools automatically manage subscriptions, verify payments and protect your content."
        ],
        'responses_ru': [
            "👥 **Инструменты для сообществ NOVA:**\n\nПолный набор для монетизации и управления сообществами:\n• Автоматическая проверка платежей\n• Кик неплательщиков\n• Приветственные сообщения\n• Анти-спам защита\n• Аналитика активности\n• Управление подписками\n\nStandard: $190 (базовое управление)\nEnterprise: $590 (полная автоматизация платежей)",
            "💰 **Монетизация сообществ:**\n\nПревратите ваше Telegram сообщество в источник стабильного дохода. Наши инструменты автоматически управляют подписками, проверяют платежи и защищают ваш контент."
        ]
    }
}

# Fallback responses in both languages
FALLBACK_RESPONSES_EN = [
    "I specialize in professional business automation. Could you rephrase your question about our solutions, prices, or delivery?",
    "Our expertise is in creating systems that provide immediate value. Perhaps you'd like to know about pricing, delivery timelines, or technical specifications?",
    "For Enterprise versions, we offer complete customization to match your exact business needs. We can adjust AI personality, integration points, and features to your requirements.",
    "Could you specify what you'd like to know? I can help with pricing, features, technical details, or customization options for our solutions."
]

FALLBACK_RESPONSES_RU = [
    "Я специализируюсь на профессиональной автоматизации бизнеса. Можете переформулировать вопрос про наши решения, цены или доставку?",
    "Наша экспертиза - создание систем, которые приносят пользу сразу. Возможно, вас интересуют цены, сроки доставки или технические детали?",
    "Для Enterprise версий мы предлагаем полную кастомизацию под ваш бизнес. Мы можем настроить личность AI, точки интеграции и функции под ваши требования.",
    "Можете уточнить, что именно вас интересует? Я могу помочь с ценами, функциями, техническими деталями или вариантами кастомизации наших решений."
]

def detect_language(text):
    """Detect language of the text (RU/EN)"""
    ru_chars = sum(1 for char in text.lower() if 'а' <= char <= 'я' or char == 'ё')
    return 'ru' if ru_chars > len(text) / 3 else 'en'

def get_intent_and_language(user_text):
    """Get intent and language based on user text"""
    user_text_lower = user_text.lower()
    language = detect_language(user_text)
    
    best_intent = None
    best_score = 0
    
    for intent, data in KNOWLEDGE_BASE.items():
        # Check English keywords
        for keyword in data.get('keywords_en', []):
            if keyword in user_text_lower:
                score = len(keyword) * 2
                if score > best_score:
                    best_score = score
                    best_intent = intent
        
        # Check Russian keywords (if Russian language detected)
        if language == 'ru':
            for keyword in data.get('keywords_ru', []):
                if keyword in user_text_lower:
                    score = len(keyword) * 2
                    if score > best_score:
                        best_score = score
                        best_intent = intent
    
    # Check with SequenceMatcher for fuzzy matching
    if best_score < 3:
        for intent, data in KNOWLEDGE_BASE.items():
            for keyword in data.get('keywords_en', []):
                score = SequenceMatcher(None, user_text_lower, keyword).ratio()
                if score > 0.7 and score > best_score:
                    best_score = score
                    best_intent = intent
            
            if language == 'ru':
                for keyword in data.get('keywords_ru', []):
                    score = SequenceMatcher(None, user_text_lower, keyword).ratio()
                    if score > 0.7 and score > best_score:
                        best_score = score
                        best_intent = intent
    
    return best_intent if best_score > 0.7 else None, language

# --- KEYBOARDS ---
def get_main_keyboard():
    """Main keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚡ OPEN NOVA SYSTEM", web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton(text="💰 Prices & Products"), KeyboardButton(text="🚀 Fast Delivery")],
            [KeyboardButton(text="💳 Crypto Payments"), KeyboardButton(text="🔧 Technical Support")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Select action or type your question..."
    )

def get_products_keyboard():
    """Products keyboard"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🤖 AI Agents", callback_data="product_ai")],
            [InlineKeyboardButton(text="🌐 Data Scrapers", callback_data="product_scraper")],
            [InlineKeyboardButton(text="👥 Community Tools", callback_data="product_comm")],
            [InlineKeyboardButton(text="💰 All Prices", callback_data="all_prices")]
        ]
    )

# --- HANDLERS ---

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "🟦 **NOVA SYSTEMS**\n\n"
        "Professional automation for Telegram business.\n\n"
        "We create systems that:\n"
        "• Work 24/7 without breaks\n"
        "• Scale to millions of users\n"
        "• Provide immediate value\n\n"
        "🇺🇸 Focused on US/EU markets\n"
        "✅ Professional solutions\n\n"
        "👇 **Initialize the system:**",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    
    # Notify admin about new user
    if ADMIN_ID:
        await bot.send_message(
            ADMIN_ID,
            f"👤 New user:\n"
            f"ID: {message.from_user.id}\n"
            f"Username: @{message.from_user.username}\n"
            f"Name: {message.from_user.full_name}"
        )

@dp.message(F.text == "💰 Prices & Products")
async def show_prices(message: types.Message):
    await message.answer(
        "💰 **NOVA Investment Structure:**\n\n"
        "🤖 **Automated Agents:**\n"
        "• Standard: $290 (basic functionality)\n"
        "• Enterprise: $890 (full customization)\n\n"
        "🌐 **Data Scrapers:**\n"
        "• Standard: $250 (1 source)\n"
        "• Enterprise: $750 (up to 5 sources)\n\n"
        "👥 **Community Tools:**\n"
        "• Standard: $190 (basic management)\n"
        "• Enterprise: $590 (full automation)\n\n"
        "🎯 **All licenses include:**\n"
        "- One-time payment\n"
        "- Lifetime use\n"
        "- Complete source code\n"
        "- 30-day support\n\n"
        "Select a product for details:",
        reply_markup=get_products_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "🚀 Fast Delivery")
async def show_delivery(message: types.Message):
    await message.answer(
        "⚡ **NOVA Delivery Process:**\n\n"
        "1. **Crypto Payment** → Instant confirmation\n"
        "2. **System Setup** → 2-4 hours\n"
        "3. **Testing** → Your approval\n"
        "4. **Final** → Complete package\n\n"
        "⏱️ **Delivery Time:**\n"
        "• Standard versions: 1 business day\n"
        "• Enterprise versions: 1-3 business days\n\n"
        "📦 **Included:**\n"
        "✓ Source Code\n"
        "✓ Installation Manual\n"
        "✓ Config Files\n"
        "✓ Setup Assistance (1h)\n"
        "✓ Private Support Channel",
        parse_mode="Markdown"
    )

@dp.message(F.text == "💳 Crypto Payments")
async def show_payment(message: types.Message):
    await message.answer(
        "💳 **NOVA Payment System:**\n\n"
        "We accept only cryptocurrency:\n\n"
        "✅ **Why crypto is better:**\n"
        "• Instant confirmation\n"
        "• No personal data\n"
        "• Available worldwide\n"
        "• Low fees (save 3-5%)\n"
        "• No payment reversal risk\n\n"
        "💰 **Accepted currencies:**\n"
        "• USDT (TRC20/ERC20)\n"
        "• TON\n"
        "• Bitcoin\n"
        "• Ethereum\n\n"
        f"**Payment Wallet:**\n"
        f"`{USDT_WALLET}`\n\n"
        "Send transaction hash after payment for activation.",
        parse_mode="Markdown"
    )

@dp.message(F.text == "🔧 Technical Support")
async def show_support(message: types.Message):
    await message.answer(
        "🛡️ **NOVA SYSTEMS Support:**\n\n"
        "**Included with every purchase:**\n"
        "✓ 30 days technical support\n"
        "✓ Installation and setup help\n"
        "✓ Fix any issues\n"
        "✓ Answer questions\n\n"
        "**Lifetime benefits:**\n"
        "✓ Security updates\n"
        "✓ Critical bug fixes\n"
        "✓ Community access\n"
        "✓ Documentation updates\n\n"
        "**Enterprise adds:**\n"
        "✓ Priority 24/7 support\n"
        "✓ Direct developer access\n"
        "✓ Custom feature requests\n"
        "✓ Monthly check-ins\n\n"
        "Our goal is your success.",
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("product_"))
async def handle_product_query(callback: types.CallbackQuery):
    product_type = callback.data.split("_")[1]
    
    if product_type == "ai":
        response = (
            "🤖 **NOVA Automated Agents:**\n\n"
            "Systems that work like your best employee, but without breaks:\n\n"
            "**Standard ($290):**\n"
            "• Smart Auto-Reply\n"
            "• Admin Panel (Basic)\n"
            "• Context Memory (24 hours)\n"
            "• Languages: EN & RU\n"
            "• Integration: Telegram + Web\n\n"
            "**Enterprise ($890):**\n"
            "• Advanced Responses\n"
            "• Full Dashboard\n"
            "• Unlimited Memory\n"
            "• Multi-Language\n"
            "• Full Customization\n"
            "• All Platforms + API\n\n"
            "Perfect for: customer support, sales, lead collection."
        )
    elif product_type == "scraper":
        response = (
            "🌐 **NOVA Data Scrapers:**\n\n"
            "Professional data collection from protected websites:\n\n"
            "**Standard ($250):**\n"
            "• Target Sites: 1 Source\n"
            "• Speed: Standard\n"
            "• Export: CSV/Excel/JSON\n"
            "• Alerts: Email\n"
            "• Proxy Support: Basic\n\n"
            "**Enterprise ($750):**\n"
            "• Target Sites: Up to 5\n"
            "• Speed: Real-time\n"
            "• Export: API + Webhooks\n"
            "• Alerts: Telegram Instant\n"
            "• Proxy Support: Advanced\n"
            "• Anti-Detect Technology\n\n"
            "Perfect for: price monitoring, competitor analysis, data collection."
        )
    elif product_type == "comm":
        response = (
            "👥 **NOVA Community Tools:**\n\n"
            "Complete automation of community management and monetization:\n\n"
            "**Standard ($190):**\n"
            "• Anti-Spam: AI Filtering\n"
            "• Welcome Msg: Text + Media\n"
            "• Payments: Manual Verify\n"
            "• Max Users: 10,000\n"
            "• Analytics: Basic\n\n"
            "**Enterprise ($590):**\n"
            "• Anti-Spam: Advanced AI\n"
            "• Welcome: Custom Media + Voice\n"
            "• Payments: Auto USDT/TON\n"
            "• Max Users: Unlimited\n"
            "• Analytics: Advanced\n"
            "• Auto-Kick: Non-Payers\n\n"
            "Perfect for: channel monetization, group management, content protection."
        )
    elif product_type == "all_prices":
        response = (
            "💰 **Complete Price Structure:**\n\n"
            "🤖 AI Agents: $290 / $890\n"
            "🌐 Data Scrapers: $250 / $750\n"
            "👥 Community Tools: $190 / $590\n\n"
            "**All versions include:**\n"
            "- One-time payment\n"
            "- Lifetime license\n"
            "- Full source code\n"
            "- 30-day support\n\n"
            "Enterprise adds full customization and priority support."
        )
    
    await callback.message.answer(response, parse_mode="Markdown")
    await callback.answer()

@dp.message(F.content_type == "web_app_data")
async def handle_web_app_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        
        if data['type'] == 'contact':
            await message.answer(
                "👨‍💻 **Developer channel activated**\n\n"
                "I've forwarded your request directly to the developer. They'll contact you shortly.\n\n"
                "Meanwhile, you can ask any questions - I'll help with the technical part.",
                reply_markup=get_main_keyboard()
            )
            
            # Save message for restoration
            save_pending_message(
                message.from_user.id,
                message.from_user.username,
                "Requested contact with developer via web app"
            )
            
            if ADMIN_ID:
                await bot.send_message(
                    ADMIN_ID,
                    f"📞 **CONTACT REQUEST**\n"
                    f"User requested contact with developer\n"
                    f"ID: {message.from_user.id}\n"
                    f"Username: @{message.from_user.username}\n"
                    f"Name: {message.from_user.full_name}"
                )
            return

        if data['type'] == 'order':
            cart_items = data['cart']
            total = data['total']
            
            cart_text = "\n".join([f"• {item['name']} - ${item['price']}" for item in cart_items])
            
            # Determine delivery time
            has_pro = any(item.get('tier') == 'pro' for item in cart_items)
            delivery_time = "1-3 business days (customization may extend)" if has_pro else "1 business day"
            
            response = (
                f"✅ **INVOICE CREATED**\n\n"
                f"📦 **Your order:**\n"
                f"{cart_text}\n"
                f"──────────────\n"
                f"💎 **Total: ${total}**\n\n"
                f"🚀 **Delivery:** {delivery_time}\n\n"
                f"💳 **Cryptocurrency Payment:**\n"
                f"Wallet (TRC20):\n"
                f"`{USDT_WALLET}`\n\n"
                f"**Instructions:**\n"
                f"1. Send ${total} to the wallet above\n"
                f"2. Send transaction hash (Transaction Hash)\n"
                f"3. We activate delivery within an hour\n\n"
                f"After payment you receive:\n"
                f"✓ Complete source code\n"
                f"✓ Installation guide\n"
                f"✓ Access to private support\n"
                f"✓ Setup assistance (1 hour)"
            )
            
            await message.answer(response, parse_mode="Markdown")
            
            # Save order for restoration
            order_data = {
                'username': message.from_user.username,
                'user_id': message.from_user.id,
                'cart': cart_items,
                'total': total,
                'delivery_time': delivery_time
            }
            save_pending_order(order_data)
            
            # Notify admin
            if ADMIN_ID:
                order_details = "\n".join([f"- {item['name']} (${item['price']})" for item in cart_items])
                await bot.send_message(
                    ADMIN_ID,
                    f"💰 **NEW ORDER!**\n\n"
                    f"User: @{message.from_user.username}\n"
                    f"ID: {message.from_user.id}\n"
                    f"Amount: ${total}\n\n"
                    f"**Order:**\n{order_details}\n\n"
                    f"**Delivery:** {delivery_time}"
                )
            
            return

    except Exception as e:
        logging.error(f"Error processing web_app_data: {e}")
        await message.answer("⚠️ An error occurred processing your data. Please try again.")

@dp.message(F.text)
async def handle_text_message(message: types.Message):
    user_text = message.text
    user_id = message.from_user.id
    
    # Save message for restoration
    save_pending_message(user_id, message.from_user.username, user_text)
    
    # Get intent and language
    intent, language = get_intent_and_language(user_text)
    
    if intent and intent in KNOWLEDGE_BASE:
        # Get appropriate response based on language
        responses = KNOWLEDGE_BASE[intent].get(f'responses_{language}', KNOWLEDGE_BASE[intent]['responses_en'])
        response = responses[hash(str(user_id)) % len(responses)]
        
        await message.answer(response, parse_mode="Markdown")
        
        # If question about payment - add wallet
        if intent == 'payment':
            await message.answer(
                f"**Payment Wallet (TRC20):**\n`{USDT_WALLET}`\n\n"
                "Send transaction hash after payment.",
                parse_mode="Markdown"
            )
        
        # Mark message as processed
        mark_message_processed(user_id, user_text)
            
    else:
        # No matching intent found
        if language == 'ru':
            response = FALLBACK_RESPONSES_RU[hash(str(user_id)) % len(FALLBACK_RESPONSES_RU)]
        else:
            response = FALLBACK_RESPONSES_EN[hash(str(user_id)) % len(FALLBACK_RESPONSES_EN)]
        
        await message.answer(response, parse_mode="Markdown")
        
        # Also send to admin for knowledge base improvement
        if ADMIN_ID:
            await bot.send_message(
                ADMIN_ID,
                f"🤔 **UNPROCESSED QUERY**\n"
                f"From: @{message.from_user.username}\n"
                f"ID: {message.from_user.id}\n"
                f"Message: {user_text}\n"
                f"Language: {language}\n\n"
                f"Bot replied: {response}"
            )

@dp.message(F.reply_to_message)
async def handle_admin_reply(message: types.Message):
    """Handle admin replies to users"""
    if str(message.from_user.id) != ADMIN_ID:
        return
    
    original_message = message.reply_to_message.text
    
    # Extract user ID from original message
    user_id_match = re.search(r"ID: (\d+)", original_message)
    if user_id_match:
        user_id = int(user_id_match.group(1))
        
        try:
            await bot.send_message(
                user_id,
                f"👨‍💻 **Response from developer:**\n\n{message.text}"
            )
            await message.answer("✅ Response sent to user.")
            
            # Extract user message text from original
            message_match = re.search(r"Message: (.+)", original_message)
            if message_match:
                user_message = message_match.group(1)
                # Mark as processed
                mark_message_processed(user_id, user_message)
                
        except Exception as e:
            await message.answer(f"❌ Error sending: {e}")
    else:
        await message.answer("❌ Could not find user ID in message.")

@dp.message(Command("status"))
async def status_command(message: types.Message):
    """Check bot status and pending messages"""
    if str(message.from_user.id) != ADMIN_ID:
        await message.answer("⚠️ Access denied.")
        return
    
    try:
        # Count pending messages
        pending_messages = 0
        if os.path.exists(MESSAGES_FILE):
            with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                messages = json.load(f)
            pending_messages = sum(1 for msg in messages if not msg['processed'])
        
        # Count pending orders
        pending_orders = 0
        if os.path.exists(ORDERS_FILE):
            with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
                orders = json.load(f)
            pending_orders = sum(1 for order in orders if not order['processed'])
        
        await message.answer(
            f"🤖 **Bot Status**\n\n"
            f"🟢 Online and working\n"
            f"📨 Pending messages: {pending_messages}\n"
            f"💰 Pending orders: {pending_orders}\n"
            f"💾 Data files: {os.path.getsize(MESSAGES_FILE) if os.path.exists(MESSAGES_FILE) else 0} bytes\n\n"
            f"Last check: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.answer(f"❌ Error checking status: {e}")

async def main():
    # Delete webhook and start polling
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Restore pending data from files
    await restore_pending_data()
    
    logging.info("🟢 NOVA SYSTEMS bot started and ready!")
    logging.info(f"🤖 Token: {TOKEN[:10]}...")
    logging.info(f"👑 Admin: {ADMIN_ID}")
    logging.info(f"💾 Data directory: {DATA_DIR}")
    
    if ADMIN_ID:
        await bot.send_message(
            ADMIN_ID, 
            "🟢 **NOVA SYSTEMS bot restarted successfully!**\n\n"
            "✅ All pending messages and orders have been restored\n"
            "✅ Bot is ready to process new requests\n"
            "✅ Data recovery system is active\n\n"
            "Use /status to check current state."
        )
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())