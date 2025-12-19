import os
import json
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

# --- НАСТРОЙКИ ---
load_dotenv()
TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID") # Убедись, что это есть в .env (только цифры)
# ССЫЛКА НА ТВОЙ САЙТ (GITHUB PAGES)
WEBAPP_URL = "https://nwl01234.github.io/portfolio-app/" 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- КЛАВИАТУРА ---
def get_main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🚀 Open Services App", web_app=WebAppInfo(url=WEBAPP_URL))],
        [KeyboardButton(text="💬 Contact Support / Ask Question")]
    ], resize_keyboard=True)

# --- START ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "👋 **Welcome to NextGen Automation.**\n\n"
        "I build high-end Telegram bots and Scrapers for the US market.\n"
        "Tap the button below to see prices, demos, and order instantly.",
        reply_markup=get_main_kb(),
        parse_mode="Markdown"
    )

# --- ОБРАБОТКА ЗАКАЗА ИЗ WEB APP ---
@dp.message(F.content_type == "web_app_data")
async def web_app_order(message: types.Message):
    data = json.loads(message.web_app_data.data)
    
    if data.get('type') == 'order':
        # Формируем текст заказа
        items_str = "\n".join([f"- {i['name']} (${i['price']})" for i in data['cart']])
        
        # 1. Ответ клиенту
        await message.answer(
            f"✅ **Order Received!**\n\n"
            f"{items_str}\n"
            f"**Total:** {data['total']}\n"
            f"**Payment Method:** {data['method'].upper()}\n\n"
            f"⏳ Wait a moment. An admin will send you the wallet address here.",
            parse_mode="Markdown"
        )
        
        # 2. Уведомление Админу
        if ADMIN_ID:
            await bot.send_message(
                ADMIN_ID,
                f"🚨 **NEW ORDER!**\n"
                f"👤 Client: @{message.from_user.username} (ID: `{message.from_user.id}`)\n\n"
                f"{items_str}\n"
                f"💰 Total: {data['total']}\n"
                f"💳 Method: {data['method']}\n\n"
                f"👉 To reply/send wallet, use:\n`/reply {message.from_user.id} Hello, here is the wallet...`",
                parse_mode="Markdown"
            )

# --- РЕЖИМ ПОДДЕРЖКИ (ЧАТ) ---

# 1. Клиент нажал кнопку "Contact Support"
@dp.message(F.text == "💬 Contact Support / Ask Question")
async def support_mode(message: types.Message):
    await message.answer("📩 Write your message here. I will reply ASAP.")

# 2. Админ отвечает клиенту (/reply ID ТЕКСТ)
@dp.message(Command("reply"))
async def reply_to_user(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return # Игнорируем чужих
    
    try:
        # Разбиваем сообщение: /reply 123456 Привет как дела
        parts = message.text.split(maxsplit=2)
        user_id = int(parts[1])
        text = parts[2]
        
        # Шлем пользователю от имени бота
        await bot.send_message(user_id, f"👨‍💻 **Admin:**\n{text}", parse_mode="Markdown")
        await message.answer("✅ Sent.")
    except Exception as e:
        await message.answer(f"⚠️ Error. Format: `/reply USER_ID MESSAGE`\nError: {e}")

# 3. Любое другое сообщение от клиента -> Пересылаем Админу
@dp.message()
async def forward_to_admin(message: types.Message):
    # Если пишет НЕ админ
    if str(message.from_user.id) != str(ADMIN_ID):
        if ADMIN_ID:
            await bot.send_message(
                ADMIN_ID,
                f"📩 **Msg from @{message.from_user.username}** (`{message.from_user.id}`):\n\n"
                f"{message.text}",
                parse_mode="Markdown"
            )

# ЗАПУСК
if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))