import asyncio
import json
import logging
import os
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID") 
USDT_WALLET = os.getenv("USDT_WALLET")
WEBAPP_URL = os.getenv("WEBAPP_URL")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- CONTENT & KEYWORDS ---
KEYWORDS = {
    'price': "Prices depend on complexity.\n\n• Core Solutions: $190 - $290\n• Pro Systems: $600 - $1200\n\nCheck the Portfolio App for exact details.",
    'buy': "Please open the App to select your package. I accept USDT.",
    'crypto': "I can build crypto scrapers, wallet trackers, and payment gateways.",
    'human': "I am an automated assistant. The developer reads this chat directly. Please leave your message.",
    'scam': "We work via Escrow or verified transactions. Check our portfolio for live demos.",
    'hello': "Greetings. How can I optimize your business today?",
    'start': "System Ready."
}

def get_smart_reply(text):
    text = text.lower()
    for key, response in KEYWORDS.items():
        if key in text:
            return response
    return None

# --- KEYBOARD ---
def kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="⚡ OPEN SYSTEM PORTFOLIO", web_app=WebAppInfo(url=WEBAPP_URL))]
    ], resize_keyboard=True)

# --- START ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "🟦 **NOVA | SYSTEMS**\n\n"
        "Premium Telegram Automation Studio.\n"
        "🇺🇸 US Market Standards.\n\n"
        "**Capabilities:**\n"
        "• AI Sales Agents (GPT-4)\n"
        "• High-Load Data Scrapers\n"
        "• Community Management Empires\n\n"
        "👇 **Click below to see live demos & pricing.**",
        reply_markup=kb(),
        parse_mode="Markdown"
    )

# --- WEB APP DATA HANDLER ---
@dp.message(F.content_type == "web_app_data")
async def web_data(message: types.Message):
    data = json.loads(message.web_app_data.data)
    
    # 1. Если нажали кнопку CONTACT в приложении
    if data['type'] == 'contact':
        await message.answer(
            "👨‍💻 **Direct Support Channel**\n\n"
            "I am here. Please describe your task or ask a question.\n"
            "I usually reply within 10 minutes.",
            parse_mode="Markdown"
        )
        return

    # 2. Если оформили ЗАКАЗ
    if data['type'] == 'order':
        cart_str = "\n".join([f"▫️ {i['name']} (${i['price']})" for i in data['cart']])
        total = data['total']
        is_pro = any('PRO' in i['name'] for i in data['cart'])

        # Ответ клиенту
        note = "\n\n⚡ **PRIORITY QUEUE ACTIVE** (PRO Tier)" if is_pro else ""
        await message.answer(
            f"✅ **INVOICE GENERATED**\n\n"
            f"{cart_str}\n"
            f"──────────────\n"
            f"💰 **TOTAL: ${total}**\n\n"
            f"Payment Method: USDT (TRC20)\n"
            f"`{USDT_WALLET}`\n"
            f"(Tap to copy){note}\n\n"
            f"⚠️ **Next Step:** Please send the transaction hash or a screenshot here to begin development.",
            parse_mode="Markdown"
        )

        # Админу
        await bot.send_message(
            ADMIN_ID,
            f"🔥 **HOT LEAD! NEW ORDER**\n"
            f"User: @{message.from_user.username} [ID: {message.from_user.id}]\n\n"
            f"{cart_str}\n"
            f"💵 Total: ${total}"
        )

# --- CHAT LOGIC ---
@dp.message(F.text)
async def chat(message: types.Message):
    # ADMIN REPLY
    if str(message.from_user.id) == str(ADMIN_ID):
        if message.reply_to_message:
            try:
                original = message.reply_to_message.text or message.reply_to_message.caption
                # Ищем ID в формате [ID: 12345]
                match = re.search(r"\[ID: (\d+)\]", original)
                if match:
                    user_id = match.group(1)
                    await bot.send_message(user_id, f"👨‍💻 **Dev:** {message.text}", parse_mode="Markdown")
                    await message.answer("✅ Sent.")
                else:
                    await message.answer("⚠️ ID not found in original message.")
            except Exception as e:
                await message.answer(f"❌ Error: {e}")
        return

    # USER MESSAGE
    if "OPEN SYSTEM" in message.text: return

    # 1. Сначала пробуем умный ответ бота
    smart_ans = get_smart_reply(message.text)
    if smart_ans:
        await message.answer(smart_ans)
    else:
        # 2. Если бот не знает ответа, он форвардит админу
        await bot.send_message(
            ADMIN_ID,
            f"📩 **MSG** from @{message.from_user.username} [ID: {message.from_user.id}]\n\n"
            f"{message.text}"
        )
        # И говорит юзеру, что передал
        await message.answer("Request received. Developer notified.")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())