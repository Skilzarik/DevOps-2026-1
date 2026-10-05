from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg://postgres:admin@localhost:5432/music_store"
print(f"Пытаемся подключиться к: {DB_URL}")

try:
    engine = create_engine(DB_URL)
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    print("✅ Подключение к БД успешно!")
except Exception as e:
    print(f"❌ Ошибка подключения!")
    print(f"Текст ошибки от БД: {e}")