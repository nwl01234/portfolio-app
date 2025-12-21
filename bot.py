import asyncio
import json
import logging
import os
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

# Настройки
load_dotenv()
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID") # Числовой ID!
USDT_WALLET = os.getenv("USDT_WALLET")
WEBAPP_URL = os.getenv("WEBAPP_URL") # https://твой_ник.github.io/portfolio-app/

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- КЛАВИАТУРА ---
def kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="⚡ OPEN NOVA SYSTEMS", web_app=WebAppInfo(url=WEBAPP_URL))],
        [KeyboardButton(text="💬 Contact Dev")]
    ], resize_keyboard=True)

# --- START ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "🟦 **NOVA | Telegram Systems**\n\n"
        "Professional development studio.\n"
        "• AI Agents & Integration\n"
        "• High-Load Scrapers\n"
        "• Community Automation\n\n"
        "👇 **Tap below to configure your project.**",
        reply_markup=kb(),
        parse_mode="Markdown"
    )

# --- ОБРАБОТКА ЗАКАЗА ---
@dp.message(F.content_type == "web_app_data")
async def web_data(message: types.Message):
    data = json.loads(message.web_app_data.data)
    if data['type'] == 'order':
        cart_str = "\n".join([f"▫️ {i['name']} (${i['price']})" for i in data['cart']])
        total = data['total']

        # 1. Ответ клиенту (с кошельком)
        await message.answer(
            f"✅ **Request Received**\n\n"
            f"Project Estimate: **${total}**\n\n"
            f"To proceed with the development, please send the deposit to:\n"
            f"`{USDT_WALLET}`\n"
            f"(Tap to copy USDT TRC20)\n\n"
            f"📩 Once paid, send a screenshot here.",
            parse_mode="Markdown"
        )

        # 2. Уведомление админу
        await bot.send_message(
            ADMIN_ID,
            f"🚨 **NEW ORDER**\n"
            f"Client: {message.from_user.full_name} (@{message.from_user.username})\n"
            f"[ID: {message.from_user.id}]\n\n" # ВАЖНО: ID для парсинга
            f"{cart_str}\n"
            f"💰 Total: ${total}"
        )

# --- ЧАТ ПОДДЕРЖКИ (В ОБЕ СТОРОНЫ) ---
@dp.message(F.text)
async def chat(message: types.Message):
    # АДМИН ПИШЕТ ОТВЕТ
    if str(message.from_user.id) == str(ADMIN_ID):
        if message.reply_to_message:
            try:
                # Ищем ID в тексте оригинального сообщения (формат [ID: 123])
                original = message.reply_to_message.text or message.reply_to_message.caption
                match = re.search(r"\[ID: (\d+)\]", original)
                
                if match:
                    user_id = match.group(1)
                    await bot.send_message(user_id, f"👨‍💻 **Dev:** {message.text}", parse_mode="Markdown")
                    await message.answer("✅ Sent.")
                else:
                    await message.answer("⚠️ Cannot find ID in that message.")
            except Exception as e:
                await message.answer(f"❌ Error: {e}")
        return

    # КЛИЕНТ ПИШЕТ СООБЩЕНИЕ
    if "OPEN NOVA" not in message.text and "Contact" not in message.text:
        await bot.send_message(
            ADMIN_ID,
            f"📩 **MSG** from {message.from_user.full_name}\n"
            f"@{message.from_user.username} [ID: {message.from_user.id}]\n\n"
            f"{message.text}"
        )
        await message.answer("Message sent. I will reply shortly.")
    elif "Contact" in message.text:
        await message.answer("Write your question or attach a screenshot:")

# --- ЗАПУСК ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())