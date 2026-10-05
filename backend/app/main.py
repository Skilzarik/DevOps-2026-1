from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from . import models
from sqlalchemy import text
from .database import SessionLocal
from .routes import users, musicians, discs, sales

app = FastAPI(
    title="Music Store API",
    description="API for music store management system",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(musicians.router)
app.include_router(discs.router)
app.include_router(sales.router)

@app.get("/health")
def healthcheck():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": "disconnected", "error": str(e)}
    finally:
        db.close()

app.mount("/static", StaticFiles(directory="../frontend"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('../frontend/index.html')