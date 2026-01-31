from sqlalchemy import create_engine

from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, echo=True) # echo = print to console

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    ...
#майбутні моделі будуть наслідуватись від цього класу.

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
