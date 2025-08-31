import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_URL = os.getenv("DB_URL")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

ADMINS = [int(admin_id) for admin_id in os.getenv("ADMINS").split(",")] if os.getenv("ADMINS") else []

TRIGGER_WORDS = [
    'температур', 'боль', 'кровотеч', 'давлен', 'понос',
    'рвот', 'диаре', 'головокруж', 'сознан'
]