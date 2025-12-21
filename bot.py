import asyncio
import json
import logging
import os
import re
from difflib import SequenceMatcher
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

# --- BRAIN: FUZZY LOGIC (НЕЧЕТКАЯ ЛОГИКА) ---

# База знаний: Ключи - это то, что мы хотим определить. Значения - список вариантов написания
KNOWLEDGE_BASE = {
    'hello': ['hello', 'hi', 'hey', 'start', 'good morning', 'wazzap', 'sup', 'privet', 'zdarova', 'hola', 'yo'],
    'price': ['price', 'cost', 'how much', 'money', 'expensive', 'cheap', 'pay', 'stoimost', 'cena'],
    'scam': ['scam', 'trust', 'reviews', 'fake', 'real', 'garant', 'proof'],
    'human': ['human', 'person', 'support', 'admin', 'dev', 'developer', 'talk', 'contact'],
    'ai': ['ai', 'gpt', 'bot', 'agent', 'smart'],
    'parsing': ['parser', 'scraper', 'data', 'mining', 'monitoring'],
}

RESPONSES = {
    'hello': "Systems Online. 🟢\nI am NOVA. I build high-load systems for Telegram.\n\nTell me, what are you looking for?\n• AI Agents\n• Scrapers\n• Community Management",
    'price': "My solutions are modular:\n\n🔹 **Core Editions:** $190 - $290 (One-time)\n🔸 **PRO Editions:** $600 - $900 (Scalable)\n\nHourly rate for custom code: $40/hr.\nCheck the Portfolio App for details.",
    'scam': "I understand the concern. We work transparently:\n\n1. You see the Demo in the App.\n2. We can use Escrow.\n3. I provide full source code for PRO tiers.",
    'human': "I've alerted the lead developer. He will read this chat shortly. Please leave your message.",
    'ai': "My AI agents handle sales and support without sleeping. They use fuzzy logic (like me right now) or GPT-4 integration.",
    'parsing': "I specialize in data extraction. I can bypass Cloudflare, rotate proxies, and scrape Amazon/Binance in real-time."
}

def get_intent(user_text):
    """Определяет намерение пользователя с учетом опечаток"""
    user_text = user_text.lower()
    best_intent = None
    highest_score = 0.0

    for intent, variants in KNOWLEDGE_BASE.items():
        for variant in variants:
            # Считаем схожесть (0.0 до 1.0)
            score = SequenceMatcher(None, user_text, variant).ratio()
            # Также проверяем частичное совпадение (если слово есть внутри фразы)
            if variant in user_text:
                score = 0.9
            
            if score > highest_score:
                highest_score = score
                best_intent = intent

    # Порог срабатывания 0.6 (60% похожести)
    if highest_score > 0.6:
        return best_intent
    return None

# --- HANDLERS ---

@dp.message(Command("start"))
async def start(message: types.Message):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="⚡ OPEN NOVA SYSTEM", web_app=WebAppInfo(url=WEBAPP_URL))]
    ], resize_keyboard=True)
    
    await message.answer(
        "🟦 **NOVA | SYSTEMS**\n\n"
        "Advanced Telegram Automation.\n"
        "Data Extraction • AI Agents • Community Tools\n\n"
        "🇺🇸 Targeting US/EU Markets.\n"
        "👇 **Initialize System below:**",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@dp.message(F.content_type == "web_app_data")
async def web_data(message: types.Message):
    data = json.loads(message.web_app_data.data)
    
    if data['type'] == 'contact':
        await message.answer("👨‍💻 **Developer Channel Open**\nType your question. I'm listening.")
        return

    if data['type'] == 'order':
        cart_text = "\n".join([f"- {i['name']} (${i['p']})" for i in data['cart']])
        
        await message.answer(
            f"✅ **INVOICE CREATED**\n\n"
            f"{cart_text}\n"
            f"──────────────\n"
            f"Total: **${data['total']}**\n\n"
            f"Wallet (TRC20):\n`{USDT_WALLET}`\n\n"
            f"Please send the hash/screenshot to begin.",
            parse_mode="Markdown"
        )
        await bot.send_message(ADMIN_ID, f"💰 NEW ORDER!\nTotal: ${data['total']}\nUser: @{message.from_user.username}")

@dp.message(F.text)
async def chat_logic(message: types.Message):
    # ADMIN REPLY LOGIC
    if str(message.from_user.id) == str(ADMIN_ID):
        if message.reply_to_message:
            original = message.reply_to_message.text
            match = re.search(r"\[ID: (\d+)\]", original)
            if match:
                await bot.send_message(match.group(1), f"👨‍💻 **Dev:** {message.text}")
            return

    # USER LOGIC
    intent = get_intent(message.text)
    
    if intent and intent in RESPONSES:
        # Бот понял, о чем речь
        await message.answer(RESPONSES[intent], parse_mode="Markdown")
    else:
        # Бот не понял -> шлет админу и говорит юзеру
        await bot.send_message(
            ADMIN_ID, 
            f"📩 **UNKNOWN QUERY**\nFrom: @{message.from_user.username} [ID: {message.from_user.id}]\nMsg: {message.text}"
        )
        await message.answer(
            "I am analyzing your request... It requires human expertise.\n"
            "⚠️ **Developer notified.** Expect a reply shortly."
        )

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())