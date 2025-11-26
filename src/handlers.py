from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from config import TRIGGER_WORDS, ADMINS
from states import UserState, AdminState
from keyboards import (
    get_period_keyboard, get_feedback_keyboard, get_cancel_keyboard,
    get_main_menu_keyboard, get_useful_materials_keyboard, get_more_materials_keyboard,
    get_support_subscription_keyboard
)
from database import (
    save_user, update_user_period, get_stats, get_period_stats, increment_question_count,
    get_user_data, get_all_user_ids, save_message_to_history, get_message_history,
    get_users_with_daily_support, toggle_daily_support, is_daily_support_enabled
)
from utils import ask_deepseek
from daily_support import get_today_message

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, pool):
    # Проверяем, зарегистрирован ли пользователь
    async with pool.acquire() as conn:
        user = await get_user_data(conn, message.from_user.id)
    
    if user:
        # Пользователь уже зарегистрирован - просто показываем меню
        await state.set_state(UserState.main)
        await state.update_data(name=user['name'], period=user['period'])
        await message.answer(
            "Выбери, что тебя интересует:",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        # Новый пользователь - начинаем регистрацию
        await state.set_state(UserState.name)
        await message.answer(
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
        "Какой у тебя сейчас период?",
        reply_markup=get_period_keyboard()
    )

@router.message(UserState.period)
async def process_period(message: Message, state: FSMContext, pool):
    period = message.text.lower().strip()
    
    # Нормализуем период
    period_map = {
        "готовлюсь": "готовлюсь",
        "беременна": "беременна",
        "ребенку меньше года": "ребенку меньше года",
        "ребенку 2-3": "ребенку 2-3",
        "ребенку 3+": "ребенку 3+"
}

    normalized_period = period_map.get(period, period)
    await state.update_data(period=normalized_period)
    
    # Обновляем период пользователя в БД
    async with pool.acquire() as conn:
        await update_user_period(conn, message.from_user.id, normalized_period)
    
    # Получаем имя для приветствия
    user_data = await state.get_data()
    name = user_data.get('name', '')
    
    # Отправляем информацию о возможностях бота
    welcome_text = f"""Отлично, {name}! Здесь ты найдёшь:

 • полезные видео и материалы от стилистов, психологов и карьерных консультантов

 • поддержку во время беременности и материнства, ты точно не одна

 • проверенные материалы по уходу за собой и ребёнком (без диагнозов)

• каждый день — короткое сообщение поддержки, чтобы ты не чувствовала себя одна

А вот чего тут нет:

 🚫 диагнозов

 🚫 токсичных советов

 🚫 осуждения

Если не знаешь, с чего начать, нажимай на кнопку "Посмотреть полезные материалы", мы подготовили видео от стилиста, психолога и карьерного консультанта 🙂"""
    
    await state.set_state(UserState.main)
    await message.answer(welcome_text, reply_markup=get_main_menu_keyboard())
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
    
@router.message(Command("send"))
async def cmd_send(message: Message, state: FSMContext):
    """Команда для админов для рассылки сообщений всем пользователям"""
    #print(f"DEBUG: Команда /send получена от пользователя {message.from_user.id}, ADMINS={ADMINS}", flush=True)
    
    if message.from_user.id not in ADMINS:
        #print(f"DEBUG: Пользователь {message.from_user.id} не является админом", flush=True)
        return
    
    #print(f"DEBUG: Устанавливаем состояние AdminState.waiting_broadcast", flush=True)
    await state.set_state(AdminState.waiting_broadcast)
    current_state = await state.get_state()
    #print(f"DEBUG: Текущее состояние после установки: {current_state}", flush=True)
    
    await message.answer(
        "📢 Режим рассылки\n\n"
        "Отправьте сообщение, которое хотите разослать всем пользователям.\n"
        "Поддерживаются любые типы сообщений: текст, фото, видео, голосовые и т.д.",
        reply_markup=get_cancel_keyboard()
    )

@router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Отмена рассылки"""
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("❌ Рассылка отменена")
    await callback.answer()

@router.message(AdminState.waiting_broadcast)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot, pool):
    """Обработка сообщения для рассылки"""
    import sys
    #print(f"DEBUG: process_broadcast вызван, user_id={message.from_user.id}, ADMINS={ADMINS}", flush=True)
    sys.stdout.flush()
    
    if message.from_user.id not in ADMINS:
        #print(f"DEBUG: Пользователь {message.from_user.id} не является админом")
        return
    
    #print(f"DEBUG: Начинаем рассылку, тип сообщения: {type(message)}", flush=True)
    
    # Получаем список всех пользователей
    async with pool.acquire() as conn:
        user_ids = await get_all_user_ids(conn)
        #print(f"DEBUG: Получены user_ids из БД: {user_ids}", flush=True)
    
    total_users = len(user_ids)
    if total_users == 0:
        await message.answer("❌ В базе данных нет пользователей для рассылки")
        await state.clear()
        return
    
    # Логируем для отладки
    #print(f"Рассылка: найдено {total_users} пользователей: {user_ids}", flush=True)
    
    # Отправляем сообщение о начале рассылки
    status_msg = await message.answer(f"📤 Начинаю рассылку для {total_users} пользователей...")
    
    success_count = 0
    failed_count = 0
    
    # Рассылаем сообщение всем пользователям
    for user_id in user_ids:
        try:
            #print(f"Попытка отправить сообщение пользователю {user_id}...", flush=True)
            # Определяем тип сообщения и отправляем соответственно
            if message.photo:
                # Фото с подписью или без
                await bot.send_photo(
                    chat_id=user_id,
                    photo=message.photo[-1].file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities
                )
            elif message.video:
                # Видео
                await bot.send_video(
                    chat_id=user_id,
                    video=message.video.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities
                )
            elif message.audio:
                # Аудио
                await bot.send_audio(
                    chat_id=user_id,
                    audio=message.audio.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities
                )
            elif message.voice:
                # Голосовое сообщение
                await bot.send_voice(
                    chat_id=user_id,
                    voice=message.voice.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities
                )
            elif message.video_note:
                # Кружочек (видео-заметка)
                await bot.send_video_note(
                    chat_id=user_id,
                    video_note=message.video_note.file_id
                )
            elif message.document:
                # Документ
                await bot.send_document(
                    chat_id=user_id,
                    document=message.document.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities
                )
            elif message.sticker:
                # Стикер
                await bot.send_sticker(
                    chat_id=user_id,
                    sticker=message.sticker.file_id
                )
            elif message.animation:
                # GIF
                await bot.send_animation(
                    chat_id=user_id,
                    animation=message.animation.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities
                )
            elif message.text:
                # Текстовое сообщение
                #print(f"DEBUG: Отправляем текстовое сообщение пользователю {user_id}: {message.text[:50]}...", flush=True)
                # Используем entities если они есть, но не parse_mode (он может отсутствовать)
                send_kwargs = {"chat_id": user_id, "text": message.text}
                if message.entities:
                    send_kwargs["entities"] = message.entities
                await bot.send_message(**send_kwargs)
            else:
                # Для других типов используем copy_message
                #print(f"DEBUG: Используем copy_message для пользователя {user_id}", flush=True)
                await bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id
                )
            success_count += 1
            #print(f"✅ Сообщение успешно отправлено пользователю {user_id}", flush=True)
        except Exception as e:
            failed_count += 1
            error_msg = str(e)
            #print(f"Ошибка при отправке пользователю {user_id}: {error_msg}", flush=True)
            # Логируем детали ошибки для отладки
            if "chat not found" in error_msg.lower() or "blocked" in error_msg.lower():
                #print(f"  -> Пользователь {user_id} заблокировал бота или чат не найден", flush=True)
                pass
            elif "forbidden" in error_msg.lower():
                #print(f"  -> Бот заблокирован пользователем {user_id}", flush=True)
                pass
            else:
                #print(f"  -> Другая ошибка: {error_msg}", flush=True)
                pass
    
    # Обновляем статус
    await status_msg.edit_text(
        f"✅ Рассылка завершена!\n\n"
        f"✅ Успешно: {success_count}\n"
        f"❌ Ошибок: {failed_count}\n"
        f"📊 Всего: {total_users}"
    )
    
    await state.clear()
    
    
# Обработка главного меню
@router.message(UserState.main)
async def process_main_menu(message: Message, state: FSMContext, pool, bot: Bot):
    user_text = message.text
    
    if user_text == "Посмотреть полезные материалы":
        await message.answer(
            "Выбери категорию:",
            reply_markup=get_useful_materials_keyboard()
        )
    elif user_text == "Задать вопрос":
        await state.set_state(UserState.waiting_question)
        await message.answer(
            "Напиши свой вопрос, и я постараюсь помочь 💕",
            reply_markup=ReplyKeyboardRemove()
        )
    elif user_text == "Получить порцию поддержки":
        # Получаем сегодняшнее сообщение поддержки
        support_message = get_today_message()
        
        # Проверяем, подписан ли пользователь на ежедневную поддержку
        async with pool.acquire() as conn:
            is_subscribed = await is_daily_support_enabled(conn, message.from_user.id)
        
        # Отправляем сообщение поддержки
        await message.answer(support_message)
        
        # Отправляем сообщение с подписью и кнопкой подписки
        if is_subscribed:
            caption = "Вы подписаны на ежедневную поддержку. Каждое утро в 9:00 вы будете получать сообщение поддержки от Милы."
        else:
            caption = "Если не подписаны, подпишитесь и получайте поддержку от Милы каждое утро."
        
        await message.answer(
            caption,
            reply_markup=get_support_subscription_keyboard(is_subscribed)
        )
    else:
        # Если это не команда меню, возможно пользователь хочет задать вопрос
        await state.set_state(UserState.waiting_question)
        await process_question(message, state, pool, bot)

# Обработка вопросов с контекстом
@router.message(UserState.waiting_question)
async def process_question_handler(message: Message, state: FSMContext, pool, bot: Bot):
    user_text = message.text
    
    # Если пользователь нажал кнопку меню, обрабатываем как меню
    if user_text in ["Посмотреть полезные материалы", "Задать вопрос", "Получить порцию поддержки"]:
        await state.set_state(UserState.main)
        await process_main_menu(message, state, pool, bot)
        return
    
    # Иначе обрабатываем как вопрос
    await process_question(message, state, pool, bot)

# Функция обработки вопроса (используется из разных мест)
async def process_question(message: Message, state: FSMContext, pool, bot: Bot):
    user_data = await state.get_data()
    user_text = message.text
    
    # Проверяем, что это текстовое сообщение
    if not user_text:
        await message.answer(
            "Пожалуйста, отправьте текстовое сообщение для вопроса.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.set_state(UserState.main)
        return
    
    if any(trigger in user_text.lower() for trigger in TRIGGER_WORDS):
        await message.answer(
            "🚨 ВНИМАНИЕ! При таких симптомах необходимо НЕМЕДЛЕННО обратиться к врачу или вызвать скорую помощь.\n\n"
            "Это не вопрос для чат-бота. Пожалуйста, не теряйте время - обратитесь за медицинской помощи прямо сейчас!",
            reply_markup=get_main_menu_keyboard()
        )
        await state.set_state(UserState.main)
        return
    
    # Получаем историю сообщений для контекста
    async with pool.acquire() as conn:
        message_history = await get_message_history(conn, message.from_user.id, limit=10)
        await increment_question_count(conn, message.from_user.id)
        user_question_count = await conn.fetchval(
            "SELECT question_count FROM users WHERE user_id = $1",
            message.from_user.id
        )
    
    # Отправляем вопрос в LLM с контекстом
    gpt_response = await ask_deepseek(
        user_text,
        user_data.get('name', ''),
        user_data.get('period', ''),
        message_history=message_history
    )
    
    if gpt_response is None:
        await message.answer(
            "🚨 ВНИМАНИЕ! При таких симптомах необходимо НЕМЕДЛЕННО обратиться к врачу или вызвать скорую помощь.\n\n"
            "Это не вопрос для чат-бота. Пожалуйста, не теряйте время - обратитесь за медицинской помощи прямо сейчас!",
            reply_markup=get_main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        await state.set_state(UserState.main)
    else:
        # Сохраняем сообщения в историю
        async with pool.acquire() as conn:
            await save_message_to_history(conn, message.from_user.id, "user", user_text)
            await save_message_to_history(conn, message.from_user.id, "assistant", gpt_response)
        
        await state.update_data(
            last_question=user_text,
            last_answer=gpt_response
        )
        
        # Показываем кнопку обратной связи после 1, 3 и 30 ответов
        show_feedback = user_question_count in [1, 3, 30]
        
        # Используем клавиатуру меню, чтобы пользователь мог вернуться или продолжить диалог
        reply_markup = get_feedback_keyboard() if show_feedback else get_main_menu_keyboard()
        await message.answer(
            gpt_response + "\n\n⚠️ Важно! Я не заменяю врача. При серьезных симптомах обращайся к специалисту.",
            reply_markup=reply_markup
        )
        
        # Остаемся в состоянии ожидания вопроса для продолжения диалога
        # Пользователь может задать следующий вопрос (будет обработан как вопрос)
        # или нажать кнопку меню (будет обработан как команда меню)
        
        # Отправляем уведомление админам (с обработкой ошибок)
        for admin_id in ADMINS:
            try:
                await bot.send_message(
                    admin_id,
                    f"Пользователь ({user_data.get('period')}) {message.from_user.full_name} (@{message.from_user.username}) спросил:\n"
                    f"{user_text}\n\n"
                    f"Ответ: {gpt_response}\n"
                    f"Всего вопросов от пользователя: {user_question_count}"
                )
            except Exception as e:
                #print(f"Ошибка при отправке сообщения админу {admin_id}: {e}")
                pass


@router.callback_query(F.data == "menu")
async def menu_callback(callback: CallbackQuery, state: FSMContext, pool):
    """Обработка нажатия на кнопку 'Меню' - аналогично команде /start"""
    # Проверяем, зарегистрирован ли пользователь
    async with pool.acquire() as conn:
        user = await get_user_data(conn, callback.from_user.id)
    
    if user:
        # Пользователь уже зарегистрирован - просто показываем меню
        await state.set_state(UserState.main)
        await state.update_data(name=user['name'], period=user['period'])
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "Выбери, что тебя интересует:",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        # Новый пользователь - начинаем регистрацию
        await state.set_state(UserState.name)
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "Как тебя зовут?",
            reply_markup=ReplyKeyboardRemove()
        )
    
    await callback.answer()

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
    
    # Отправляем админам обратную связь (с обработкой ошибок)
    for admin_id in ADMINS:
        try:
            await bot.send_message(
                admin_id,
                f"Обратная связь от пользователя ({data.get('period')}) {message.from_user.full_name} (@{message.from_user.username}):\n\n"
                f"Вопрос: {data['last_question']}\n\n"
                f"Ответ: {data['last_answer']}\n\n"
                f"Обратная связь: {feedback_text}"
            )
        except Exception as e:
            #print(f"Ошибка при отправке обратной связи админу {admin_id}: {e}")
            pass
    
    await state.set_state(UserState.main)
    await message.answer("Спасибо за вашу обратную связь! 💕")
    
# Обработка callback для подписки/отписки на поддержку
@router.callback_query(F.data.in_(["subscribe_support", "unsubscribe_support"]))
async def handle_support_subscription(callback: CallbackQuery, pool):
    """Обработка подписки/отписки на ежедневную поддержку"""
    user_id = callback.from_user.id
    is_subscribe = callback.data == "subscribe_support"
    
    async with pool.acquire() as conn:
        await toggle_daily_support(conn, user_id, is_subscribe)
        is_subscribed = await is_daily_support_enabled(conn, user_id)
    
    if is_subscribe:
        message_text = "✅ Вы подписаны на ежедневную поддержку! Каждое утро в 9:00 вы будете получать сообщение поддержки от Милы."
    else:
        message_text = "❌ Вы отписаны от ежедневной поддержки."
    
    await callback.message.edit_text(
        message_text,
        reply_markup=get_support_subscription_keyboard(is_subscribed)
    )
    await callback.answer()
    
# Обработка callback для полезных материалов
@router.callback_query(F.data.startswith("material_"))
async def handle_material_callback(callback: CallbackQuery):
    material_type = callback.data.split("_")[1]
    
    # Ссылки на сообщения в Telegram-канале для каждой категории
    video_urls = {
        "style": "https://t.me/mila_poleznoe/3",
        "psychology": "https://t.me/mila_poleznoe/9",
        "career": "https://t.me/mila_poleznoe/7"
    }
    
    material_names = {
        "style": "Стиль",
        "career": "Карьера",
        "psychology": "Психология"
    }
    
    if material_type in material_names and material_type in video_urls:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            f"📹 Видео: {material_names[material_type]}\n\n{video_urls[material_type]}",
            reply_markup=get_more_materials_keyboard()
        )
    
    await callback.answer()

@router.message()
async def handle_unregistered_user(message: Message, state: FSMContext, pool, bot: Bot):
    # Пропускаем сообщения в состоянии рассылки - они обрабатываются отдельным обработчиком
    current_state = await state.get_state()
    if current_state == AdminState.waiting_broadcast:
        #print(f"DEBUG: Общий обработчик пропускает сообщение - состояние AdminState.waiting_broadcast", flush=True)
        return
    
    # Проверяем, зарегистрирован ли пользователь в базе
    async with pool.acquire() as conn:
        user = await get_user_data(conn, message.from_user.id)
    
    if user:
        # Если пользователь найден в базе, восстанавливаем его состояние
        current_state = await state.get_state()
        if current_state is None:
            await state.set_state(UserState.main)
        
        await state.update_data(
            name=user['name'],
            period=user['period']
        )
        
        # Если пользователь в главном меню, обрабатываем как меню
        if await state.get_state() == UserState.main:
            await process_main_menu(message, state, pool, bot)
        # Если пользователь в режиме вопроса, обрабатываем как вопрос
        elif await state.get_state() == UserState.waiting_question:
            await process_question(message, state, pool, bot)
        else:
            # По умолчанию - главное меню
            await state.set_state(UserState.main)
            await process_main_menu(message, state, pool, bot)
    else:
        # Если пользователь не найден, предлагаем начать с /start
        await message.answer(
            "Пожалуйста, начните с команды /start",
            reply_markup=ReplyKeyboardRemove()
        )