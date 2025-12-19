import os
from dotenv import load_dotenv

load_dotenv()

# Основные настройки
BOT_TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
APP_URL = os.getenv("WEBAPP_URL")

# Крипто-кошельки
USDT_WALLET = os.getenv("USDT_WALLET", "ВАШ_USDT_АДРЕС_ЗДЕСЬ")
BTC_WALLET = os.getenv("BTC_WALLET", "ВАШ_BTC_АДРЕС_ЗДЕСЬ")

# Проверка загрузки
print("=== CONFIG LOADED ===")
print(f"BOT_TOKEN loaded: {'✅' if BOT_TOKEN else '❌'}")
print(f"ADMIN_ID loaded: {'✅' if ADMIN_ID else '❌'}")
print(f"APP_URL loaded: {'✅' if APP_URL else '❌'}")
print(f"USDT_WALLET: {USDT_WALLET}")
print(f"BTC_WALLET: {BTC_WALLET}")
print("=====================")

if not BOT_TOKEN:
    print("❌ CRITICAL: BOT_TOKEN not found in .env!")
    exit(1)