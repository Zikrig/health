import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import create_db_pool, init_db
from handlers import router
from scheduler import schedule_daily_messages

async def main():
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    dp.include_router(router)
    
    pool = await create_db_pool()
    await init_db(pool)
    
    # Запускаем планировщик ежедневных сообщений в фоне
    asyncio.create_task(schedule_daily_messages(bot, pool))
    
    # Запускаем бота с дополнительными параметрами
    await dp.start_polling(bot, pool=pool, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())