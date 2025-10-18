# app/api/deps.py
from typing import Generator
from app.db.session import SessionLocal

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
