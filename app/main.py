from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.projects import router as project_router
from app.api.v1.documents import router as document_router
from app.api.v1.chat import router as chat_router
from app.api.v1.study import router as study_router

app = FastAPI()
origins = [
    "http://localhost:3000",  # React / Next.js
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Або заміни на origins, якщо хочеш суворіше
    allow_credentials=True,
    allow_methods=["*"],  # Дозволити всі методи (GET, POST, DELETE...)
    allow_headers=["*"],  # Дозволити всі заголовки (Authorization, Content-Type...)
)
app.include_router(auth_router)
app.include_router(project_router)
app.include_router(document_router)
app.include_router(chat_router)
app.include_router(study_router)



@app.get("/")
def read_root():
    return {"Hello": "zxc"}



@app.get("/db-health")
async def db_health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        print(f"Database error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "OK"}
