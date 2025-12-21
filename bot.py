import os
import sys
import json
import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Настройка логирования
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
USDT_WALLET = os.getenv("USDT_WALLET")
WEBAPP_URL = os.getenv("WEBAPP_URL")

# Проверка конфигурации
if not all([TOKEN, ADMIN_ID, USDT_WALLET, WEBAPP_URL]):
    logging.error("❌ ОШИБКА: Не заполнен файл .env! Проверьте переменные.")
    sys.exit(1)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- КЛАВИАТУРЫ ---
def main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🚀 Open Portfolio App", web_app=WebAppInfo(url=WEBAPP_URL))],
        [KeyboardButton(text="💬 Support / Contact Dev")]
    ], resize_keyboard=True, input_field_placeholder="Select an option...")

# --- ОБРАБОТЧИКИ КОМАНД ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"👋 **Hello, {message.from_user.first_name}!**\n\n"
        "I am a Premium Bot Developer specializing in AI, Data Scraping, and Community management.\n\n"
        "👇 **Click below to see my interactive portfolio, live demos, and prices.**",
        reply_markup=main_kb(),
        parse_mode="Markdown"
    )

@dp.message(Command("id"))
async def cmd_id(message: types.Message):
    await message.answer(f"Your ID: `{message.from_user.id}`", parse_mode="Markdown")

# --- ОБРАБОТКА ЗАКАЗОВ ИЗ MINI APP ---

@dp.message(F.content_type == "web_app_data")
async def handle_webapp_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        
        if data.get('type') == 'order':
            order_id = message.message_id
            items = data['items']
            total = data['total']
            payment_method = data['payment_method']
            
            # Формирование списка товаров
            items_str = "\n".join([f"🔹 {item['name']} — ${item['price']}" for item in items])
            
            # 1. Ответ Клиенту
            payment_instr = ""
            if payment_method == 'usdt':
                payment_instr = (
                    f"💎 **Payment via USDT (TRC20)**\n"
                    f"Address: `{USDT_WALLET}`\n"
                    f"⚠️ Click address to copy. Send screenshot after payment."
                )
            else:
                payment_instr = "👛 **Payment via Telegram Wallet**\nWait for invoice."

            await message.answer(
                f"✅ **ORDER RECEIVED #{order_id}**\n\n"
                f"{items_str}\n\n"
                f"💰 **Total: ${total}**\n"
                f"------------------\n"
                f"{payment_instr}",
                parse_mode="Markdown"
            )
            
            # 2. Уведомление Админу
            admin_text = (
                f"🚨 **NEW ORDER!**\n"
                f"👤 Client: {message.from_user.full_name} (@{message.from_user.username})\n"
                f"🆔 ID: `{message.from_user.id}`\n\n"
                f"{items_str}\n"
                f"💰 Profit: ${total}\n"
                f"💳 Method: {payment_method}"
            )
            await bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")

    except Exception as e:
        logging.error(f"Error handling WebApp data: {e}")
        await message.answer("⚠️ System Error. Please contact support.")

# --- СИСТЕМА ПОДДЕРЖКИ (МЕССЕНДЖЕР) ---

@dp.message(F.text == "💬 Support / Contact Dev")
async def support_handler(message: types.Message):
    await message.answer("✍️ **Write your message below.**\nI will receive it instantly and reply here.")

@dp.message(F.text)
async def chat_logic(message: types.Message):
    # Логика: Если пишет Админ
    if str(message.from_user.id) == str(ADMIN_ID):
        # Если это ответ на пересланное сообщение
        if message.reply_to_message:
            # Пытаемся извлечь ID пользователя из текста оригинального сообщения (если бот форвардил текстом)
            # Или используем встроенный механизм reply
            try:
                # В данном простом варианте мы ищем ID в тексте, который бот прислал админу
                # Но лучше всего работает метод copy_message, если админ отвечает на репост
                if message.reply_to_message.forward_from:
                    user_id = message.reply_to_message.forward_from.id
                    await bot.copy_message(chat_id=user_id, from_chat_id=message.chat.id, message_id=message.message_id)
                    await message.answer("✅ Reply sent via Message Copy.")
                else:
                    # Если пользователь скрыл аккаунт при пересылке, пробуем парсить текст
                    text_parts = message.reply_to_message.text.split("ID: ")
                    if len(text_parts) > 1:
                        user_id = text_parts[1].split()[0].replace('`', '')
                        await bot.copy_message(chat_id=user_id, from_chat_id=message.chat.id, message_id=message.message_id)
                        await message.answer("✅ Reply sent via ID parsing.")
                    else:
                        await message.answer("⚠️ Cannot find User ID to reply. Ask user to open profile.")
            except Exception as e:
                await message.answer(f"❌ Error sending reply: {e}")
        return

    # Логика: Если пишет Клиент -> Пересылаем Админу
    # Игнорируем сервисные команды
    if message.text and not message.text.startswith('/'):
        # Формируем красивое уведомление
        await bot.send_message(
            ADMIN_ID,
            f"📩 **MSG FROM CLIENT**\n"
            f"👤: {message.from_user.full_name} (@{message.from_user.username})\n"
            f"ID: `{message.from_user.id}`\n"
            f"Text: {message.text}",
            parse_mode="Markdown"
        )
        # Пересылаем оригинал (чтобы видеть файлы/фото если будут)
        await message.forward(ADMIN_ID)

# --- ЗАПУСК ---
async def main():
    print("✅ BOT STARTED. Ready to serve.")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())