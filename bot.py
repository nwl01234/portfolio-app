import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN, APP_URL

# Настройка логирования
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# Инициализация
dp = Dispatcher()

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    Обработчик команды /start
    """
    user_name = html.quote(message.from_user.full_name)
    
    # Создаем клавиатуру с кнопкой Web App
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🚀 Open Portfolio App", 
        web_app=WebAppInfo(url=APP_URL)
    )
    
    text = (
        f"Hi, {user_name}! 👋\n\n"
        f"I am a **Full-Stack Bot Developer** ready to automate your business.\n\n"
        f"👇 **Click the button below** to launch my interactive portfolio inside Telegram.\n"
        f"You will see live demos of e-commerce, analytics, and automation tools."
    )
    
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.MARKDOWN)

async def main() -> None:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")