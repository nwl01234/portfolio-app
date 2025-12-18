import os
import json
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo
from dotenv import load_dotenv

# Загрузка настроек
load_dotenv()
TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID") # Вставь свой ID в .env!

# Настройка бота
bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# URL твоего Web App (с GitHub Pages)
WEBAPP_URL = "https://nwl01234.github.io/portfolio-app/" # <-- ПРОВЕРЬ ССЫЛКУ!

# --- 1. СТАРТ И МЕНЮ ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    kb = [
        [types.KeyboardButton(text="🚀 Open Portfolio App", web_app=WebAppInfo(url=WEBAPP_URL))],
        [types.KeyboardButton(text="💬 Contact Support")]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await message.answer(
        "👋 **Welcome to NextGen Automation.**\n\n"
        "Tap the button below to explore our Premium Bots, AI Agents, and Scrapers.\n"
        "Direct crypto payments accepted.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# --- 2. ОБРАБОТКА ЗАКАЗА ИЗ WEB APP ---
@dp.message(F.content_type == "web_app_data")
async def web_app_order(message: types.Message):
    data = json.loads(message.web_app_data.data)
    
    if data['type'] == 'order':
        # 1. Ответ клиенту
        await message.answer(
            f"✅ **Order Received!**\n\n"
            f"Items: {data['items']}\n"
            f"Total: ${data['total']}\n"
            f"Payment: {data['payment']}\n\n"
            f"Please wait. An admin will send you the wallet address shortly.",
            parse_mode="Markdown"
        )
        
        # 2. Уведомление тебе (Админу)
        if ADMIN_ID:
            await bot.send_message(
                ADMIN_ID,
                f"🚨 **NEW ORDER!**\n\n"
                f"👤 Client: @{message.from_user.username} (ID: {message.from_user.id})\n"
                f"📦 Order: {data['items']}\n"
                f"💰 Amount: ${data['total']}\n"
                f"💳 Method: {data['payment']}\n\n"
                f"⚠️ *Reply to this message to send wallet address!*"
            )

# --- 3. СИСТЕМА ПОДДЕРЖКИ (ОБЩЕНИЕ) ---

# Если клиент нажал "Contact Support"
@dp.message(F.text == "💬 Contact Support")
async def contact_support(message: types.Message):
    await message.answer("📝 Please write your message below. Our team receives it instantly.")

# Пересылка сообщений от клиента админу
@dp.message(F.from_user.id != int(ADMIN_ID or 0))
async def handle_client_message(message: types.Message):
    if not message.web_app_data: # Исключаем данные веб-аппа
        if ADMIN_ID:
            await bot.send_message(
                ADMIN_ID,
                f"📩 **Message from @{message.from_user.username}** (ID: {message.from_user.id}):\n\n"
                f"{message.text}"
            )
            # Сохраняем ID последнего писавшего (для упрощения, в идеале нужна БД)
            # Но проще использовать Reply (Ответ) в самом Телеграм

# Ответ админа клиенту (через Reply)
@dp.message(F.from_user.id == int(ADMIN_ID or 0))
async def handle_admin_reply(message: types.Message):
    if message.reply_to_message:
        # Пытаемся вытащить ID из текста пересланного сообщения
        # Это "хак", лучше всего работает, если ты отвечаешь на форвард
        try:
            # Парсим ID из текста уведомления (если оно было системным)
            # Или просто отвечаем, если это пересланное сообщение
             pass # Тут нужна логика сохранения ID, но проще так:
             
             # САМЫЙ ПРОСТОЙ СПОСОБ ОТВЕТИТЬ:
             # Когда тебе приходит сообщение "Message from...", там есть ID.
             # Тебе нужно скопировать ID и использовать команду /send ID ТЕКСТ
             # Или допишем это сейчас ниже.
        except:
            pass
    else:
        pass

# Команда для ответа: /reply ID ТЕКСТ
@dp.message(Command("reply"))
async def admin_reply_cmd(message: types.Message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    
    try:
        # Пример: /reply 123456789 Hello!
        args = message.text.split(maxsplit=2)
        user_id = int(args[1])
        text = args[2]
        
        await bot.send_message(user_id, f"👨‍💻 **Support:**\n{text}")
        await message.answer("✅ Sent.")
    except:
        await message.answer("⚠️ Use format: `/reply USER_ID Your message`")

# Запуск
if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))