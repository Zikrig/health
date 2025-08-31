from aiogram.fsm.state import State, StatesGroup

class UserState(StatesGroup):
    name = State()
    period = State()
    main = State()
    feedback = State()
    waiting_feedback = State()