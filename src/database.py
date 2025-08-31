import asyncpg
import asyncio
from config import DB_URL

async def create_db_pool():
    max_attempts = 10
    attempt = 0
    
    while attempt < max_attempts:
        try:
            pool = await asyncpg.create_pool(DB_URL)
            print("Successfully connected to PostgreSQL")
            return pool
        except Exception as e:
            attempt += 1
            print(f"Connection attempt {attempt} failed: {e}")
            if attempt >= max_attempts:
                raise e
            await asyncio.sleep(2)  # Wait 2 seconds before retrying

async def init_db(pool):
    async with pool.acquire() as conn:
        # Создаем таблицу пользователей с полем для подсчета вопросов
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(255),
                full_name VARCHAR(255),
                name VARCHAR(255),
                period VARCHAR(255),
                question_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("Database tables checked successfully")

async def save_user(conn, user_id, username, full_name, name):
    await conn.execute(
        "INSERT INTO users (user_id, username, full_name, name) VALUES ($1, $2, $3, $4) ON CONFLICT (user_id) DO UPDATE SET name = $4",
        user_id, username, full_name, name
    )

async def update_user_period(conn, user_id, period):
    await conn.execute(
        "UPDATE users SET period = $1 WHERE user_id = $2",
        period, user_id
    )

async def increment_question_count(conn, user_id):
    await conn.execute(
        "UPDATE users SET question_count = question_count + 1 WHERE user_id = $1",
        user_id
    )

async def get_stats(conn):
    user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
    total_questions = await conn.fetchval("SELECT SUM(question_count) FROM users")
    return user_count, total_questions

async def get_period_stats(conn):
    return await conn.fetch("""
        SELECT 
            period,
            COUNT(*) as user_count,
            SUM(question_count) as total_questions  -- Добавляем суммарное количество вопросов
        FROM users 
        WHERE period IS NOT NULL
        GROUP BY period
        ORDER BY user_count DESC
    """)
    
    # database.py
async def get_user_data(conn, user_id):
    row = await conn.fetchrow(
        "SELECT name, period FROM users WHERE user_id = $1",
        user_id
    )
    return dict(row) if row else None