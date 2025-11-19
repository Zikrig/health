import aiohttp
import re
from config import DEEPSEEK_API_KEY, TRIGGER_WORDS

async def ask_deepseek(question: str, user_name: str, period: str, message_history=None) -> str:
    """Отправка вопроса в DeepSeek API с учетом истории сообщений"""
    if any(re.search(rf'\b{word}', question.lower()) for word in TRIGGER_WORDS):
        return None
    
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }

    system_prompt = f"""Ты — тёплый, спокойный помощник для женщин на этапах беременности и материнства. Отвечай кратко, без диагнозов, без осуждения. Помни имя ({user_name}) и этап ({period}). Никогда не повторяй первоначальное приветствие. Продолжай разговор с учётом контекста. Предлагай "материалы" и "задать вопрос", когда это уместно."""

    # Формируем список сообщений для API
    messages = [{"role": "system", "content": system_prompt}]
    
    # Добавляем историю сообщений (если есть)
    if message_history:
        for msg in message_history:
            # Пропускаем служебные сообщения (например, команды)
            if msg['role'] in ['user', 'assistant'] and len(msg['content'].strip()) > 0:
                messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })
    
    # Добавляем текущий вопрос
    messages.append({
        "role": "user",
        "content": question
    })
    
    data = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                result = await response.json()
                return result['choices'][0]['message']['content']
    except Exception as e:
        #print(f"Error calling DeepSeek API: {e}")
        return "Извини, у меня временные технические трудности. Попробуй спросить позже."