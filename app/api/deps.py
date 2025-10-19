from app.db.session import SessionLocal

def get_db():
    "fastAPI dependency that yields a database session and ensures it is closed afterward"
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
