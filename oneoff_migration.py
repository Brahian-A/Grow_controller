from sqlalchemy import text
from app.db.session import engine

# Haz la migración (idempotente: ignora si ya existe)
sql = "ALTER TABLE mecanismos ADD COLUMN nivel_agua INTEGER NOT NULL DEFAULT 0;"

try:
    with engine.begin() as conn:
        conn.execute(text(sql))
    print("OK: columna nivel_agua agregada.")
except Exception as e:
    msg = str(e).lower()
    if "duplicate column name" in msg or "already exists" in msg:
        print("La columna 'nivel_agua' ya existe. Nada que hacer.")
    else:
        raise
