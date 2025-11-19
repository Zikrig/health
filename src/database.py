import asyncpg
import asyncio
from config import DB_URL

async def create_db_pool():
    max_attempts = 10
    attempt = 0
    
    while attempt < max_attempts:
        try:
            pool = await asyncpg.create_pool(DB_URL)
            #print("Successfully connected to PostgreSQL")
            return pool
        except Exception as e:
            attempt += 1
            #print(f"Connection attempt {attempt} failed: {e}")
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
                daily_support_enabled BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Добавляем колонку daily_support_enabled, если её нет (для существующих БД)
        column_exists = await conn.fetchval('''
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name = 'daily_support_enabled'
            )
        ''')
        
        if not column_exists:
            await conn.execute('''
                ALTER TABLE users 
                ADD COLUMN daily_support_enabled BOOLEAN DEFAULT FALSE
            ''')
            #print("Added daily_support_enabled column to users table")
        
        # Создаем таблицу для хранения истории сообщений (для контекста диалога)
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS message_history (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                role VARCHAR(10) NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Создаем индекс для быстрого поиска истории пользователя
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_message_history_user_id 
            ON message_history(user_id, created_at DESC)
        ''')
        
        #print("Database tables checked successfully")

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

async def get_all_user_ids(conn):
    """Получить список всех user_id из базы данных"""
    rows = await conn.fetch("SELECT user_id FROM users")
    return [row['user_id'] for row in rows]

async def save_message_to_history(conn, user_id, role, content):
    """Сохранить сообщение в историю диалога"""
    await conn.execute(
        "INSERT INTO message_history (user_id, role, content) VALUES ($1, $2, $3)",
        user_id, role, content
    )

async def get_message_history(conn, user_id, limit=10):
    """Получить последние N сообщений из истории диалога"""
    rows = await conn.fetch(
        """
        SELECT role, content 
        FROM message_history 
        WHERE user_id = $1 
        ORDER BY created_at DESC 
        LIMIT $2
        """,
        user_id, limit
    )
    # Возвращаем в обратном порядке (от старых к новым)
    return list(reversed([{"role": row['role'], "content": row['content']} for row in rows]))

async def get_users_with_daily_support(conn):
    """Получить список пользователей с включенной ежедневной поддержкой"""
    rows = await conn.fetch(
        "SELECT user_id FROM users WHERE daily_support_enabled = TRUE"
    )
    return [row['user_id'] for row in rows]

async def is_daily_support_enabled(conn, user_id):
    """Проверить, включена ли ежедневная поддержка для пользователя"""
    result = await conn.fetchval(
        "SELECT daily_support_enabled FROM users WHERE user_id = $1",
        user_id
    )
    return result if result is not None else False

async def toggle_daily_support(conn, user_id, enabled):
    """Включить/выключить ежедневную поддержку для пользователя"""
    await conn.execute(
        "UPDATE users SET daily_support_enabled = $1 WHERE user_id = $2",
        enabled, user_id
    )