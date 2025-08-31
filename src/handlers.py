from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from config import TRIGGER_WORDS, ADMINS
from states import UserState
from keyboards import get_period_keyboard, get_feedback_keyboard
from database import save_user, update_user_period, get_stats, get_period_stats, increment_question_count, get_user_data
from utils import ask_deepseek

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(UserState.name)
    await message.answer(
        "Привет! 👋 Я Мила - твой помощник во время беременности и материнства.\n\n"
        "Как тебя зовут?",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(UserState.name)
async def process_name(message: Message, state: FSMContext, pool):
    name = message.text
    await state.update_data(name=name)
    
    # Сохраняем пользователя в БД
    async with pool.acquire() as conn:
        await save_user(conn, message.from_user.id, message.from_user.username, message.from_user.full_name, name)
    
    await state.set_state(UserState.period)
    await message.answer(
        f"Приятно познакомиться, {name}! 🤗\n\n"
        "Какой у тебя сейчас период?",
        reply_markup=get_period_keyboard()
    )

period_texts = {
    "Готовлюсь": "Сейчас самое время подготовиться и узнать всё о будущих месяцах. Задавай вопросы — календарь беременности, советы, ответы врачей все рядом!",
    "Беременна": "Поздравляю с этим увлекательным путешествием! Поддержу на каждом этапе, подскажу полезные материалы, открою календарь беременности и помогу консультироваться с экспертами.",
    "Ребенку меньше года": "Первый год — время радости, вопросов и забот. Со мной ты найдёшь поддержку, советы по уходу, развитию малыша и себе.",
    "Ребенку 2-3 года": "Возраст открытий и проб — расскажем о воспитании, играх, развитии речи и поддержке мамы. Ты не одна — тут только полезное и актуальное.",
    "Ребенку 3+ года": "Для семьи с дошкольником здесь есть идеи, рекомендации по развитию, адаптации в саду и подготовке к школе — задавай любые вопросы.",
    "Я - папа": "Отлично, что вы с нами! Бот открыт для всех родителей — мужчины тоже находят полезную информацию, поддержку, советы для себя и семьи."
}

@router.message(UserState.period)
async def process_period(message: Message, state: FSMContext, pool):
    period = message.text
    await state.update_data(period=period)
    
    # Обновляем период пользователя в БД
    async with pool.acquire() as conn:
        await update_user_period(conn, message.from_user.id, period)
    
    # Отправляем соответствующий текст для периода
    if period in period_texts:
        await message.answer(period_texts[period], reply_markup=ReplyKeyboardRemove())
    
    await state.set_state(UserState.main)
    # await message.answer(
    #     "Что я умею:\n"
    #     "• Поддерживать тебя во время беременности и материнства\n"
    #     "• Давать проверенную информацию (без диагнозов)\n"
    #     "• Подсказывать, где искать полезные материалы\n"
    #     "• Делать тебе чуть легче каждый день 💕\n\n"
    #     "Чего я не делаю:\n"
    #     "🚫 Не ставлю диагнозы\n"
    #     "🚫 Не заменяю врача\n"
    #     "🚫 Не даю лекарства или назначения\n\n"
    #     "Теперь ты можешь задать любой вопрос!",
    #     reply_markup=ReplyKeyboardRemove()
    # )


@router.message(Command("stats"))
async def cmd_stats(message: Message, pool):
    if message.from_user.id not in ADMINS:
        return

    async with pool.acquire() as conn:
        user_count, question_count = await get_stats(conn)  # Теперь получаем два значения
        period_stats = await get_period_stats(conn)

    stats_text = [
        f"📊 Статистика бота:",
        f"Всего пользователей: {user_count}",
        f"Задано вопросов: {question_count}",
        "",
        "📈 Распределение по периодам:"
    ]
    
    for stat in period_stats:
        stats_text.append(f"• {stat['period']}: {stat['user_count']} пользователей, {stat['total_questions']} вопросов")

    await message.answer("\n".join(stats_text))
    
    
@router.message(UserState.main)
async def process_main(message: Message, state: FSMContext, pool, bot: Bot):
    user_data = await state.get_data()
    user_text = message.text
    
    if any(trigger in user_text.lower() for trigger in TRIGGER_WORDS):
        await message.answer(
            "🚨 ВНИМАНИЕ! При таких симптомах необходимо НЕМЕДЛЕННО обратиться к врачу или вызвать скорую помощь.\n\n"
            "Это не вопрос для чат-бота. Пожалуйста, не теряйте время - обратитесь за медицинской помощи прямо сейчас!",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    # Увеличиваем счетчик вопросов
    async with pool.acquire() as conn:
        await increment_question_count(conn, message.from_user.id)
        user_question_count = await conn.fetchval(
            "SELECT question_count FROM users WHERE user_id = $1",
            message.from_user.id
        )
    
    gpt_response = await ask_deepseek(user_text, user_data.get('name', ''), user_data.get('period', ''))
    
    if gpt_response is None:
        await message.answer(
            "🚨 ВНИМАНИЕ! При таких симптомах необходимо НЕМЕДЛЕННО обратиться к врачу или вызвать скорую помощь.\n\n"
            "Это не вопрос для чат-бота. Пожалуйста, не теряйте время - обратитесь за медицинской помощи прямо сейчас!",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await state.update_data(
            last_question=user_text,
            last_answer=gpt_response
        )
        
        # Показываем кнопку обратной связи после 1, 3 и 30 ответов
        show_feedback = user_question_count in [1, 3, 30]
        
        await message.answer(
            gpt_response + "\n\n⚠️ Важно! Я не заменяю врача. При серьезных симптомах обращайся к специалисту.",
            reply_markup=get_feedback_keyboard() if show_feedback else None
        )
        
        for admin_id in ADMINS:
            await bot.send_message(
                admin_id,
                f"Пользователь ({user_data.get('period')}) {message.from_user.full_name} (@{message.from_user.username}) спросил:\n"
                f"{user_text}\n\n"
                f"Ответ: {gpt_response}\n"
                f"Всего вопросов от пользователя: {user_question_count}"  # Добавляем информацию о количестве вопросов
            )


@router.callback_query(F.data == "feedback")
async def feedback_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserState.waiting_feedback)
    
    # Убираем кнопку обратной связи
    await callback.message.edit_reply_markup(reply_markup=None)
    
    await callback.message.answer("Пожалуйста, напишите ваш отзыв или комментарий:")

@router.message(UserState.waiting_feedback)
async def process_feedback(message: Message, state: FSMContext, bot: Bot):
    feedback_text = message.text
    data = await state.get_data()
    
    # Отправляем админам обратную связь
    for admin_id in ADMINS:
        await bot.send_message(
            admin_id,
            f"Обратная связь от пользователя ({data.get('period')}) {message.from_user.full_name} (@{message.from_user.username}):\n\n"
            f"Вопрос: {data['last_question']}\n\n"
            f"Ответ: {data['last_answer']}\n\n"
            f"Обратная связь: {feedback_text}"
        )
    
    await state.set_state(UserState.main)
    await message.answer("Спасибо за вашу обратную связь! 💕")
    
@router.message()
async def handle_unregistered_user(message: Message, state: FSMContext, pool, bot: Bot):
    # Проверяем, зарегистрирован ли пользователь в базе
    async with pool.acquire() as conn:
        user = await get_user_data(conn, message.from_user.id)
    
    if user:
        # Если пользователь найден в базе, восстанавливаем его состояние
        await state.set_state(UserState.main)
        await state.update_data(
            name=user['name'],
            period=user['period']
        )
        # Обрабатываем сообщение как обычно
        await process_main(message, state, pool, bot)
    else:
        # Если пользователь не найден, предлагаем начать с /start
        await message.answer(
            "Пожалуйста, начните с команды /start",
            reply_markup=ReplyKeyboardRemove()
        )