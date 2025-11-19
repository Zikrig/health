import asyncio
from datetime import datetime, time
from aiogram import Bot
from database import get_users_with_daily_support
from daily_support import get_today_message
from config import BOT_TOKEN

async def send_daily_messages(bot: Bot, pool):
    """Отправка ежедневных сообщений поддержки всем пользователям с включенной поддержкой"""
    async with pool.acquire() as conn:
        user_ids = await get_users_with_daily_support(conn)
    
    if not user_ids:
        return
    
    message = get_today_message()
    success_count = 0
    failed_count = 0
    
    for user_id in user_ids:
        try:
            await bot.send_message(chat_id=user_id, text=message)
            success_count += 1
        except Exception as e:
            failed_count += 1
            #print(f"Ошибка при отправке ежедневного сообщения пользователю {user_id}: {e}")
    
    #print(f"Ежедневные сообщения отправлены: успешно {success_count}, ошибок {failed_count}")

async def schedule_daily_messages(bot: Bot, pool):
    """Планировщик для отправки ежедневных сообщений в 9:00"""
    while True:
        now = datetime.now()
        target_time = time(9, 0)  # 9:00
        
        # Вычисляем время до следующего 9:00
        if now.time() < target_time:
            # Сегодня еще не было 9:00
            next_run = datetime.combine(now.date(), target_time)
        else:
            # Сегодня уже было 9:00, планируем на завтра
            from datetime import timedelta
            next_run = datetime.combine(now.date() + timedelta(days=1), target_time)
        
        wait_seconds = (next_run - now).total_seconds()
        #print(f"Следующая отправка ежедневных сообщений: {next_run} (через {wait_seconds/3600:.1f} часов)")
        
        await asyncio.sleep(wait_seconds)
        
        # Отправляем сообщения
        await send_daily_messages(bot, pool)

