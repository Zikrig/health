from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_period_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Готовлюсь"), KeyboardButton(text="Беременна")],
            [KeyboardButton(text="Ребенку меньше года")],
            [KeyboardButton(text="Ребенку 2-3 года"), KeyboardButton(text="Ребенку 3+ года")],
            [KeyboardButton(text="Я - папа")]
        ],
        resize_keyboard=True
    )

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Хочу задать вопрос или поделиться чем-то, что меня волнует")]
        ],
        resize_keyboard=True
    )


def get_feedback_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Обратная связь", callback_data="feedback")]
        ]
    )