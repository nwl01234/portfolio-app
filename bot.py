import os
import json
import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Загрузка конфига
load_dotenv()
TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
USDT_WALLET = os.getenv("USDT_WALLET")
WEBAPP_URL = os.getenv("WEBAPP_URL")

# Проверка настроек
if not TOKEN or not ADMIN_ID:
    print("❌ ОШИБКА: Не заполнен .env файл (TOKEN или ADMIN_ID)")
    exit()

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# --- ГЛАВНОЕ МЕНЮ ---
def main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📱 Открыть Портфолио и Услуги", web_app=WebAppInfo(url=WEBAPP_URL))],
        [KeyboardButton(text="💬 Написать разработчику")]
    ], resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 **Привет! Это бот студии автоматизации.**\n\n"
        "Здесь ты можешь:\n"
        "1. Попробовать наши инструменты в реальном времени.\n"
        "2. Заказать разработку (AI, Парсеры, Комьюнити).\n"
        "3. Написать напрямую разработчику.\n\n"
        "Нажми кнопку ниже ⬇️",
        reply_markup=main_kb(),
        parse_mode="Markdown"
    )

# --- ОБРАБОТКА ЗАКАЗА ИЗ WEBAPP ---
@dp.message(F.content_type == "web_app_data")
async def handle_order(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        if data['type'] == 'order':
            # 1. Формируем чек для клиента
            total = data['total']
            items_text = "\n".join([f"▫️ {item['name']} — ${item['price']}" for item in data['items']])
            
            response_text = (
                f"✅ **Заказ принят!**\n\n"
                f"{items_text}\n"
                f"💰 **Итого к оплате: ${total}**\n\n"
            )

            # Логика оплаты
            if data['method'] == 'crypto':
                response_text += (
                    f"💳 **Оплата USDT (TRC20):**\n"
                    f"`{USDT_WALLET}`\n\n"
                    f"⚠️ После перевода нажмите кнопку 'Я оплатил' или отправьте скриншот."
                )
            else:
                response_text += "💳 Для оплаты картой/Telegram Stars дождитесь счета от администратора."

            await message.answer(response_text, parse_mode="Markdown")

            # 2. Уведомление АДМИНУ
            admin_text = (
                f"🚨 **НОВЫЙ ЗАКАЗ!**\n"
                f"👤 Клиент: {message.from_user.full_name} (@{message.from_user.username})\n"
                f"🆔 ID: `{message.from_user.id}`\n\n"
                f"{items_text}\n"
                f"💵 Сумма: ${total}\n"
                f"Способ: {data['method']}"
            )
            await bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")

    except Exception as e:
        await message.answer("Ошибка обработки заказа. Напишите в поддержку.")
        logging.error(f"Order error: {e}")

# --- МЕССЕНДЖЕР (СВЯЗЬ С КЛИЕНТОМ) ---

# 1. Клиент нажал "Написать разработчику"
@dp.message(F.text == "💬 Написать разработчику")
async def msg_mode(message: types.Message):
    await message.answer("✍️ Пишите ваш вопрос прямо сюда. Я отвечу в ближайшее время.")

# 2. Пересылка сообщения от КЛИЕНТА -> АДМИНУ
@dp.message(F.from_user.id != int(ADMIN_ID))
async def forward_to_admin(message: types.Message):
    # Игнорируем сервисные сообщения
    if message.web_app_data: return 
    
    forward_text = (
        f"📩 **Сообщение от клиента**\n"
        f"От: {message.from_user.full_name} (@{message.from_user.username})\n"
        f"ID: `{message.from_user.id}`\n\n"
        f"{message.text or '[Вложение]'}"
    )
    # Пересылаем само сообщение (чтобы видеть фото/файлы) и текст с ID
    await bot.send_message(ADMIN_ID, forward_text, parse_mode="Markdown")
    try:
        await message.forward(ADMIN_ID)
    except:
        pass

# 3. Ответ АДМИНА -> КЛИЕНТУ (через Reply)
@dp.message(F.from_user.id == int(ADMIN_ID))
async def admin_reply(message: types.Message):
    # Если админ отвечает на пересланное сообщение или сообщение бота с ID
    if message.reply_to_message:
        try:
            # Вариант А: Ответ на форвард
            if message.reply_to_message.forward_from:
                user_id = message.reply_to_message.forward_from.id
            # Вариант Б: Ответ на текст бота, где есть "ID: 12345"
            else:
                lines = message.reply_to_message.text.split('\n')
                user_id_line = next((line for line in lines if "ID: " in line), None)
                if user_id_line:
                    user_id = int(user_id_line.split("`")[1]) # Вытаскиваем цифры из ID: `123`
                else:
                    await message.answer("❌ Не могу найти ID пользователя в этом сообщении.")
                    return

            # Отправка
            await bot.copy_message(chat_id=user_id, from_chat_id=message.chat.id, message_id=message.message_id)
            await message.answer("✅ Отправлено.")
            
        except Exception as e:
            await message.answer(f"❌ Ошибка отправки: {e}")
    else:
        # Если админ пишет просто так, можно добавить команду рассылки, но пока просто игнорим
        pass

# Запуск
async def main():
    print("🤖 Бот запущен...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())