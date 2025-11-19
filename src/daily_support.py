import json
import os
from datetime import datetime, date

DAILY_MESSAGES_FILE = os.path.join(os.path.dirname(__file__), 'daily_messages.json')

def load_daily_messages():
    """Загрузить данные о ежедневных сообщениях"""
    try:
        with open(DAILY_MESSAGES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Если файл не найден, создаем базовую структуру
        default_data = {
            "current_day": 0,
            "themes": []
        }
        save_daily_messages(default_data)
        return default_data

def save_daily_messages(data):
    """Сохранить данные о ежедневных сообщениях"""
    with open(DAILY_MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_today_message():
    """Получить сообщение на сегодня (одно и то же в течение дня)"""
    data = load_daily_messages()
    
    if not data.get('themes'):
        return "Ты не одна, и всё в порядке."
    
    # Получаем все сообщения из всех тем
    all_messages = []
    for theme in data['themes']:
        all_messages.extend(theme.get('messages', []))
    
    if not all_messages:
        return "Ты не одна, и всё в порядке."
    
    # Используем номер дня года для выбора сообщения (чтобы было одно и то же в течение дня)
    today = date.today()
    day_of_year = today.timetuple().tm_yday  # День года (1-365/366)
    
    # Выбираем сообщение на основе дня года
    message_index = (day_of_year - 1) % len(all_messages)
    message = all_messages[message_index]
    
    return message

