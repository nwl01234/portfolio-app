import asyncio
import json
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

# КОНФИГУРАЦИЯ
TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID") # Убедись, что это число, а не никнейм
WEBAPP_URL = os.getenv("WEBAPP_URL")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# КЛАВИАТУРА
def get_main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="⚡ OPEN APP", web_app=WebAppInfo(url=WEBAPP_URL))],
        [KeyboardButton(text="📩 Contact Support")]
    ], resize_keyboard=True)

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "⬛ **NEXUS DEV SYSTEM**\n\n"
        "Welcome. I build high-load bots, AI agents, and crypto tools.\n"
        "Open the App to see the portfolio and prices.",
        reply_markup=get_main_kb(),
        parse_mode="Markdown"
    )

# ЛОГИКА ЗАКАЗА ИЗ ПРИЛОЖЕНИЯ
@dp.message(F.content_type == "web_app_data")
async def web_app_data(message: types.Message):
    data = json.loads(message.web_app_data.data)
    
    if data['type'] == 'order':
        cart_text = "\n".join([f"• {i['name']} (${i['price']})" for i in data['cart']])
        total = data['total']
        
        # 1. Сообщение админу
        await bot.send_message(
            ADMIN_ID,
            f"💰 **NEW ORDER RECEIVED**\n"
            f"User: @{message.from_user.username}\n"
            f"ID: `{message.from_user.id}`\n\n"
            f"{cart_text}\n"
            f"💵 Total: **${total}**\n"
            f"Status: Payment Confirmation Needed"
        )
        
        # 2. Сообщение клиенту
        await message.answer(
            "✅ **Order Request Received.**\n\n"
            "I have notified the developer. Once your transaction is confirmed on the blockchain, I will contact you here to start the work.",
            parse_mode="Markdown"
        )

# ЛОГИКА ЧАТА (КЛИЕНТ -> АДМИН -> КЛИЕНТ)
@dp.message(F.text)
async def chat_handler(message: types.Message):
    # Если пишет АДМИН
    if str(message.from_user.id) == str(ADMIN_ID):
        if message.reply_to_message:
            try:
                # Извлекаем ID из текста сообщения бота (формат: ID: `12345`)
                # Это самый надежный способ без баз данных
                original_text = message.reply_to_message.text
                user_id = original_text.split("ID: `")[1].split("`")[0]
                
                await bot.send_message(user_id, f"👨‍💻 **DEV:** {message.text}")
                await message.answer("✅ Sent.")
            except Exception as e:
                await message.answer(f"❌ Error. Reply to the notification message containing user ID.\n{e}")
        return

    # Если пишет КЛИЕНТ
    if message.text != "📩 Contact Support":
        await bot.send_message(
            ADMIN_ID,
            f"📩 **MESSAGE**\nFrom: @{message.from_user.username}\nID: `{message.from_user.id}`\n\n{message.text}"
        )
        await message.answer("Message sent to developer. Wait for reply.")
    else:
        await message.answer("Write your question below:")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())