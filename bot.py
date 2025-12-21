import os
import json
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# --- КОНФИГ ---
TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
USDT_WALLET = os.getenv("USDT_WALLET")
BTC_WALLET = os.getenv("BTC_WALLET", "")
WEBAPP_URL = os.getenv("WEBAPP_URL")

if not all([TOKEN, ADMIN_ID, USDT_WALLET, WEBAPP_URL]):
    raise ValueError("Missing required environment variables")

bot = Bot(token=TOKEN, parse_mode=ParseMode.MARKDOWN)
dp = Dispatcher()

# --- МЕНЮ ---
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚡ OPEN APP", web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton(text="💬 Support Chat")],
            [KeyboardButton(text="📊 My Orders"), KeyboardButton(text="ℹ️ About")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Choose an option..."
    )

# --- МНОГОЯЗЫЧНЫЕ ОТВЕТЫ ---
RESPONSES = {
    "en": {
        "welcome": "⬛ **NWL PREMIUM DEV**\n\nWelcome. Use the App to view services and live demos.\nUse the Support Chat to contact me directly.",
        "support_online": "🟢 **Support Online.** Write your message:",
        "order_confirmed": "✅ **ORDER CONFIRMED**\n\n{items}\n\n💰 TOTAL: **{total}**\n\n{payment_info}",
        "usdt_payment": f"💎 **USDT (TRC20) PAYMENT:**\n`{USDT_WALLET}`\n\nSend screenshot after payment.",
        "wallet_payment": "👛 **WALLET PAYMENT:**\nI will send you a @wallet invoice shortly.",
        "new_order": "🚨 **NEW SALE!**\n👤 {name} (@{username})\n🆔 `{user_id}`\n\n{items}\n💰 {total} ({method})",
        "message_received": "📩 **MSG FROM CLIENT**\n👤 @{username}\n🆔 `{user_id}`\n\n{message}",
        "dev_reply": "👨‍💻 **DEV:** {message}",
        "reply_sent": "✅ Sent.",
        "reply_error": "⚠️ Reply to a message containing the User ID.",
        "no_orders": "You have no orders yet. Open the App to place your first order!",
        "about": "🤖 **NWL Premium Dev**\n\nSpecializing in:\n• AI Telegram Bots\n• Web Scrapers\n• Community Management\n• Crypto Integration\n\nFast delivery (3-5 days)\nProfessional code\nLifetime support",
        "price": "💰 **Pricing:**\n• Standard AI Bot: $200\n• Premium AI Agent: $800\n• Basic Scraper: $180\n• Monitor System: $600\n• Moderator Bot: $150\n• Community Hub: $500",
        "delivery": "🚚 **Delivery Time:**\n• Standard bots: 3 days\n• Premium projects: 5-7 days\n• Custom features: +1-2 days",
        "payment": "💳 **Payment Methods:**\n• USDT TRC20\n• Telegram Wallet\n• Bitcoin (BTC)",
        "features": "🌟 **Key Features:**\n• GPT-4 Integration\n• 24/7 Monitoring\n• Crypto Payments\n• Anti-Ban Protection\n• Analytics Dashboard",
        "support": "🆘 **Support:**\n• Lifetime support\n• Free revisions for 30 days\n• 3-day money-back guarantee",
        "portfolio": "📱 **Live Portfolio:**\nTry demos in the App:\n• AI Chat Assistant\n• Web Scraper Terminal\n• Dashboard Preview",
        "unknown": "I'm an AI assistant. Ask me about:\n• Pricing (/price)\n• Delivery time (/delivery)\n• Payment methods (/payment)\n• Features (/features)\n• Support (/support)\n• Portfolio (/portfolio)"
    },
    "ru": {
        "welcome": "⬛ **NWL PREMIUM DEV**\n\nДобро пожаловать. Используйте приложение для просмотра услуг и живых демо.\nИспользуйте чат поддержки для связи со мной напрямую.",
        "support_online": "🟢 **Поддержка онлайн.** Напишите ваше сообщение:",
        "order_confirmed": "✅ **ЗАКАЗ ПОДТВЕРЖДЁН**\n\n{items}\n\n💰 ИТОГО: **{total}**\n\n{payment_info}",
        "usdt_payment": f"💎 **ОПЛАТА USDT (TRC20):**\n`{USDT_WALLET}`\n\nОтправьте скриншот после оплаты.",
        "wallet_payment": "👛 **ОПЛАТА ЧЕРЕЗ КОШЕЛЁК:**\nЯ отправлю вам инвойс @wallet в ближайшее время.",
        "new_order": "🚨 **НОВАЯ ПРОДАЖА!**\n👤 {name} (@{username})\n🆔 `{user_id}`\n\n{items}\n💰 {total} ({method})",
        "message_received": "📩 **СООБЩЕНИЕ ОТ КЛИЕНТА**\n👤 @{username}\n🆔 `{user_id}`\n\n{message}",
        "dev_reply": "👨‍💻 **РАЗРАБОТЧИК:** {message}",
        "reply_sent": "✅ Отправлено.",
        "reply_error": "⚠️ Ответьте на сообщение, содержащее ID пользователя.",
        "no_orders": "У вас ещё нет заказов. Откройте приложение, чтобы сделать первый заказ!",
        "about": "🤖 **NWL Premium Dev**\n\nСпециализация:\n• AI Telegram боты\n• Веб-скраперы\n• Управление сообществами\n• Крипто-интеграция\n\nБыстрая доставка (3-5 дней)\nПрофессиональный код\nПожизненная поддержка",
        "price": "💰 **Цены:**\n• Стандартный AI бот: $200\n• Премиум AI агент: $800\n• Базовый скрапер: $180\n• Система мониторинга: $600\n• Бот-модератор: $150\n• Центр сообщества: $500",
        "delivery": "🚚 **Время доставки:**\n• Стандартные боты: 3 дня\n• Премиум проекты: 5-7 дней\n• Кастомные функции: +1-2 дня",
        "payment": "💳 **Способы оплаты:**\n• USDT TRC20\n• Telegram Wallet\n• Bitcoin (BTC)",
        "features": "🌟 **Ключевые особенности:**\n• Интеграция GPT-4\n• Круглосуточный мониторинг\n• Крипто-платежи\n• Защита от банов\n• Аналитическая панель",
        "support": "🆘 **Поддержка:**\n• Пожизненная поддержка\n• Бесплатные правки 30 дней\n• Гарантия возврата 3 дня",
        "portfolio": "📱 **Живое портфолио:**\nПопробуйте демо в приложении:\n• AI чат-ассистент\n• Терминал веб-скрапера\n• Превью дашборда",
        "unknown": "Я AI ассистент. Спросите меня о:\n• Ценах (/price)\n• Времени доставки (/delivery)\n• Способах оплаты (/payment)\n• Функциях (/features)\n• Поддержке (/support)\n• Портфолио (/portfolio)"
    }
}

def get_user_language(user_id: int) -> str:
    # В реальном приложении можно хранить язык пользователя в БД
    # Здесь используем английский по умолчанию
    return "en"

def get_response(key: str, user_id: int, **kwargs) -> str:
    lang = get_user_language(user_id)
    response = RESPONSES.get(lang, {}).get(key, RESPONSES["en"][key])
    return response.format(**kwargs) if kwargs else response

# --- КОМАНДЫ ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        get_response("welcome", message.from_user.id),
        reply_markup=main_menu()
    )

@dp.message(Command("price"))
async def price(message: types.Message):
    await message.answer(get_response("price", message.from_user.id))

@dp.message(Command("delivery"))
async def delivery(message: types.Message):
    await message.answer(get_response("delivery", message.from_user.id))

@dp.message(Command("payment"))
async def payment(message: types.Message):
    await message.answer(get_response("payment", message.from_user.id))

@dp.message(Command("features"))
async def features(message: types.Message):
    await message.answer(get_response("features", message.from_user.id))

@dp.message(Command("support"))
async def support(message: types.Message):
    await message.answer(get_response("support", message.from_user.id))

@dp.message(Command("portfolio"))
async def portfolio(message: types.Message):
    await message.answer(get_response("portfolio", message.from_user.id))

@dp.message(Command("about"))
async def about(message: types.Message):
    await message.answer(get_response("about", message.from_user.id))

@dp.message(Command("orders"))
async def orders(message: types.Message):
    # Здесь можно получить заказы пользователя из БД
    await message.answer(get_response("no_orders", message.from_user.id))

# --- ОБРАБОТКА ЗАКАЗА ИЗ ПРИЛОЖЕНИЯ ---
@dp.message(F.content_type == "web_app_data")
async def process_order(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        
        if data.get('type') == 'order':
            items_list = "\n".join([f"▫️ {i['name']} - ${i['price']}" for i in data['cart']])
            total = data['total']
            method = data.get('method', 'usdt')
            
            # Ответ клиенту
            if method == 'usdt':
                payment_info = get_response("usdt_payment", message.from_user.id)
            else:
                payment_info = get_response("wallet_payment", message.from_user.id)
            
            await message.answer(
                get_response("order_confirmed", message.from_user.id,
                           items=items_list, total=total, payment_info=payment_info)
            )
            
            # Уведомление админу
            await bot.send_message(
                ADMIN_ID,
                get_response("new_order", message.from_user.id,
                           name=message.from_user.full_name,
                           username=message.from_user.username or "no_username",
                           user_id=message.from_user.id,
                           items=items_list,
                           total=total,
                           method=method)
            )
            
            logger.info(f"New order from {message.from_user.id}: {total}")
            
    except Exception as e:
        logger.error(f"Error processing order: {e}")
        await message.answer("⚠️ Error processing order. Please try again.")

# --- МЕССЕНДЖЕР (КЛИЕНТ <-> АДМИН) ---
@dp.message(F.text)
async def chat_handler(message: types.Message):
    user_id = message.from_user.id
    text = message.text
    
    # Если пишет АДМИН (это ответ клиенту)
    if str(user_id) == str(ADMIN_ID):
        if message.reply_to_message:
            try:
                # Ищем ID пользователя в тексте сообщения
                txt = message.reply_to_message.text
                if "🆔 `" in txt:
                    user_id = txt.split("🆔 `")[1].split("`")[0]
                    await bot.send_message(user_id, get_response("dev_reply", user_id, message=text))
                    await message.answer(get_response("reply_sent", user_id))
                else:
                    await message.answer(get_response("reply_error", user_id))
            except Exception as e:
                logger.error(f"Error replying to client: {e}")
                await message.answer(get_response("reply_error", user_id))
        return
    
    # Если пишет КЛИЕНТ
    if text == "💬 Support Chat":
        await message.answer(get_response("support_online", user_id))
    
    elif text == "📊 My Orders":
        await orders(message)
    
    elif text == "ℹ️ About":
        await about(message)
    
    elif text == "⚡ OPEN APP":
        await message.answer("Opening portfolio app...")
    
    else:
        # Пересылаем сообщение админу
        await bot.send_message(
            ADMIN_ID,
            get_response("message_received", user_id,
                       username=message.from_user.username or "no_username",
                       user_id=user_id,
                       message=text)
        )
        
        # Авто-ответ для часто задаваемых вопросов
        lower_text = text.lower()
        if any(word in lower_text for word in ["price", "cost", "сколько", "цена"]):
            await message.answer(get_response("price", user_id))
        elif any(word in lower_text for word in ["delivery", "time", "доставк", "срок"]):
            await message.answer(get_response("delivery", user_id))
        elif any(word in lower_text for word in ["payment", "оплат", "платёж"]):
            await message.answer(get_response("payment", user_id))
        elif any(word in lower_text for word in ["feature", "function", "функц", "возможност"]):
            await message.answer(get_response("features", user_id))
        elif any(word in lower_text for word in ["support", "help", "поддерж", "помощь"]):
            await message.answer(get_response("support", user_id))
        elif any(word in lower_text for word in ["hi", "hello", "привет", "здравствуй"]):
            await message.answer(get_response("welcome", user_id))
        else:
            await message.answer(get_response("unknown", user_id))

# --- ЗАПУСК БОТА ---
async def main():
    logger.info("Bot starting...")
    
    # Удаляем вебхук и начинаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Устанавливаем команды бота
    commands = [
        types.BotCommand(command="start", description="Start the bot"),
        types.BotCommand(command="price", description="Check pricing"),
        types.BotCommand(command="delivery", description="Delivery time"),
        types.BotCommand(command="payment", description="Payment methods"),
        types.BotCommand(command="features", description="Key features"),
        types.BotCommand(command="support", description="Support information"),
        types.BotCommand(command="portfolio", description="Live portfolio"),
        types.BotCommand(command="about", description="About developer"),
        types.BotCommand(command="orders", description="My orders")
    ]
    await bot.set_my_commands(commands)
    
    logger.info("Bot is running!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped with error: {e}")