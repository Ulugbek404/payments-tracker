from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.db import init_db
from app.routers import debtors, payments, students

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Учёт оплат учебного центра", lifespan=lifespan)
app.include_router(students.router)
app.include_router(payments.router)
app.include_router(debtors.router)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")
