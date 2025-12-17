import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ВАЖНО: Сюда мы вставим ссылку ПОСЛЕ того, как загрузим mini_app на GitHub
# Пока оставь пустой или поставь заглушку
APP_URL = "https://nwl01234.github.io/portfolio-app/" 

if not BOT_TOKEN:
    exit("Error: BOT_TOKEN not found in .env file")