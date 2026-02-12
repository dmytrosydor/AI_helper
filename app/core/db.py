from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.testing import future

from app.core.config import settings

ASYNC_DATABASE_URL = settings.DATABASE_URL.replace("postgresql+psycopg2://", "postgresql+asyncpg://")

if "asyncpg" not in ASYNC_DATABASE_URL:
     ASYNC_DATABASE_URL = ASYNC_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(ASYNC_DATABASE_URL, echo=True, future = True) # echo = print to console

AsyncSessionLocal = async_sessionmaker(
    bind = engine,
    class_ = AsyncSession,
    expire_on_commit = False,
    autoflush = False
)

class Base(DeclarativeBase):
    ...
#майбутні моделі будуть наслідуватись від цього класу.

async def get_db():
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()
