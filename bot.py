import os
import json
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton

load_dotenv()

# --- КОНФИГ ---
TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID") # Твой цифровой ID
USDT_WALLET = os.getenv("USDT_WALLET") # Твой адрес кошелька Tjx...
WEBAPP_URL = os.getenv("WEBAPP_URL") # Ссылка на GitHub Pages

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- МЕНЮ ---
def main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="⚡ OPEN APP", web_app=WebAppInfo(url=WEBAPP_URL))],
        [KeyboardButton(text="💬 Support Chat")]
    ], resize_keyboard=True)

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "⬛ **NWL PREMIUM DEV**\n\n"
        "Welcome. Use the App to view services and live demos.\n"
        "Use the Support Chat to contact me directly.",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# --- ОБРАБОТКА ЗАКАЗА ИЗ ПРИЛОЖЕНИЯ ---
@dp.message(F.content_type == "web_app_data")
async def process_order(message: types.Message):
    data = json.loads(message.web_app_data.data)
    
    if data['type'] == 'order':
        items_list = "\n".join([f"▫️ {i['name']} - ${i['price']}" for i in data['cart']])
        
        # 1. Ответ клиенту
        pay_info = ""
        if data['method'] == 'usdt':
            pay_info = f"💎 **USDT (TRC20) PAYMENT:**\n`{USDT_WALLET}`\n\nSend screenshot after payment."
        else:
            pay_info = "👛 **WALLET PAYMENT:**\nI will send you a @wallet invoice shortly."

        await message.answer(
            f"✅ **ORDER CONFIRMED**\n\n{items_list}\n\n"
            f"💰 TOTAL: **{data['total']}**\n\n"
            f"{pay_info}",
            parse_mode="Markdown"
        )
        
        # 2. Ответ Админу
        await bot.send_message(
            ADMIN_ID,
            f"🚨 **NEW SALE!**\n"
            f"👤 {message.from_user.full_name} (@{message.from_user.username})\n"
            f"🆔 `{message.from_user.id}`\n\n"
            f"{items_list}\n"
            f"💰 {data['total']} ({data['method']})"
        )

# --- МЕССЕНДЖЕР (КЛИЕНТ <-> АДМИН) ---

# Если клиент нажал кнопку или пишет текст
@dp.message(F.text)
async def chat_handler(message: types.Message):
    # Если пишет АДМИН (это ответ клиенту)
    if str(message.from_user.id) == str(ADMIN_ID):
        if message.reply_to_message:
            # Пытаемся достать ID из текста сообщения (если бот переслал)
            try:
                # Ищем строку "ID: 12345"
                txt = message.reply_to_message.text
                user_id = txt.split("🆔 `")[1].split("`")[0]
                await bot.send_message(user_id, f"👨‍💻 **DEV:** {message.text}")
                await message.answer("✅ Sent.")
            except:
                await message.answer("⚠️ Reply to a message containing the User ID.")
        return

    # Если пишет КЛИЕНТ -> Пересылаем Админу
    if message.text == "💬 Support Chat":
        await message.answer("🟢 **Support Online.** Write your message:")
    else:
        await bot.send_message(
            ADMIN_ID,
            f"📩 **MSG FROM CLIENT**\n"
            f"👤 @{message.from_user.username}\n"
            f"🆔 `{message.from_user.id}`\n\n"
            f"{message.text}"
        )

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())