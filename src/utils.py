import aiohttp
import re
from config import DEEPSEEK_API_KEY, TRIGGER_WORDS

async def ask_deepseek(question: str, user_name: str, period: str) -> str:
    if any(re.search(rf'\b{word}', question.lower()) for word in TRIGGER_WORDS):
        return None
    
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }

    prompt = f"""
    Ты - дружелюбный ИИ-помощник для беременных женщин и молодых мам по имени Мила.

    Важные правила:
    - НЕ ставь диагнозы и НЕ давай конкретных медицинских рекомендаций
    - При любых серьезных симптомах обязательно рекомендуй обратиться к врачу
    - Всегда напоминай, что ты не заменяешь медицинского специалиста
    - Отвечай дружелюбно, с поддержкой, как подруга
    - Если не уверен в ответе - честно признавайся и советуй консультацию с врачом
    
    Пользователь: {user_name}, период: {period}
    Вопрос: {question}
    
    Ответ (максимум 500 символов, дружелюбный тон, без диагнозов):
    """
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": 500
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                result = await response.json()
                return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error calling DeepSeek API: {e}")
        return "Извини, у меня временные технические трудности. Попробуй спросить позже."