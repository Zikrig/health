from aiogram.fsm.state import State, StatesGroup

class UserState(StatesGroup):
    name = State()
    period = State()
    main = State()
    feedback = State()
    waiting_feedback = State()
    waiting_question = State()  # Состояние ожидания вопроса после нажатия "Задать вопрос"
    daily_support_enabled = State()  # Флаг для ежедневных сообщений

class AdminState(StatesGroup):
    waiting_broadcast = State()