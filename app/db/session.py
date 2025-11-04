from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Renombrado para consistencia con la documentación de FastAPI/SQLAlchemy
SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

# --- Configuración del Motor ---
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,
    connect_args={
        "check_same_thread": False, # Necesario para concurrencia de FastAPI
        "timeout": 30,             # Aumenta el tiempo de espera de bloqueo a 30 segundos
        "journal_mode": "WAL",     # Habilita el modo Write-Ahead Logging 
        "synchronous": "NORMAL"    # Optimización de escritura con WAL
    },
    pool_pre_ping=True,
)


# --- Configuración de la Sesión ---
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)