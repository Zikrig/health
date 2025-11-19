from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_period_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="готовлюсь"), KeyboardButton(text="беременна")],
            [KeyboardButton(text="ребенку меньше года")],
            [KeyboardButton(text="ребенку 2-3"), KeyboardButton(text="ребенку 3+")]
        ],
        resize_keyboard=True
    )

def get_main_menu_keyboard():
    """Главное меню с тремя основными опциями"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Посмотреть полезные материалы")],
            [KeyboardButton(text="Задать вопрос")],
            [KeyboardButton(text="Получить порцию поддержки")]
        ],
        resize_keyboard=True
    )

def get_useful_materials_keyboard():
    """Клавиатура для выбора категории полезных материалов"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Стиль", callback_data="material_style")],
            [InlineKeyboardButton(text="Карьера", callback_data="material_career")],
            [InlineKeyboardButton(text="Психология", callback_data="material_psychology")]
        ]
    )

def get_more_materials_keyboard():
    """Кнопка для просмотра дополнительных материалов"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Посмотреть еще", url="https://t.me/mila_poleznoe")]
        ]
    )

def get_feedback_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Обратная связь", callback_data="feedback")]
        ]
    )

def get_cancel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_broadcast")]
        ]
    )

def get_support_subscription_keyboard(is_subscribed: bool):
    """Клавиатура для подписки/отписки на ежедневную поддержку"""
    if is_subscribed:
        button_text = "Отписаться от ежедневной поддержки"
        callback_data = "unsubscribe_support"
    else:
        button_text = "Подписаться на ежедневную поддержку"
        callback_data = "subscribe_support"
    
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=button_text, callback_data=callback_data)]
        ]
    )