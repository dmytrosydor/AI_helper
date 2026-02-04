from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.db import get_db
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.projects import router as project_router
from app.api.v1.documents import router as document_router

app = FastAPI()
origins = [
    "http://localhost:3000",  # React / Next.js
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Або заміни на origins, якщо хочеш суворіше
    allow_credentials=True,
    allow_methods=["*"],  # Дозволити всі методи (GET, POST, DELETE...)
    allow_headers=["*"],  # Дозволити всі заголовки (Authorization, Content-Type...)
)
app.include_router(auth_router)
app.include_router(project_router)
app.include_router(document_router)
@app.get("/")
def read_root():
    return {"Hello": "zxc"}



@app.get("/db-health")
def db_health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))

        db.commit()
    except Exception as e:
        print(f"Database error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
