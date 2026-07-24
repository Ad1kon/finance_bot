import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DB_PATH = os.getenv("DB_PATH", "finance.db")

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN не найден. Скопируйте .env.example в .env и укажите токен бота."
    )
