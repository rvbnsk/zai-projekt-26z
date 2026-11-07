import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from sqlalchemy import select

from . import models
from .db import SessionLocal, init_schema
from .problems import problem, register_handlers
from .routers import auth, measurements, sensors, series
from .security import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

JSON_MEDIA_TYPES = ("application/json", "application/problem+json", "application/*", "*/*")


def create_admin():
    """Creates the admin account from environment variables if it does not exist yet."""
    username = os.environ["ADMIN_USERNAME"]
    with SessionLocal() as db:
        if db.scalar(select(models.User).where(models.User.username == username)) is None:
            db.add(models.User(username=username, password_hash=hash_password(os.environ["ADMIN_PASSWORD"])))
            db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_schema()
    create_admin()
    yield


app = FastAPI(title="ZAI 26Z - Serie pomiarowe", lifespan=lifespan)
register_handlers(app)


@app.middleware("http")
async def check_content_negotiation(request: Request, call_next):
    if request.url.path.startswith("/api"):
        accept = request.headers.get("accept", "")
        if accept and not any(media_type in accept for media_type in JSON_MEDIA_TYPES):
            return problem(406, "Only application/json responses are available")

        has_body = int(request.headers.get("content-length", "0") or 0) > 0
        content_type = request.headers.get("content-type", "")
        if request.method in ("POST", "PUT", "PATCH") and has_body and not content_type.startswith("application/json"):
            return problem(415, "Request body must be application/json")

    return await call_next(request)


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(series.router)
app.include_router(sensors.router)
app.include_router(measurements.router)
