"""FastAPI app entrypoint."""
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.routers import calls, token, voice, webhooks

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Telemedicine Click-to-Call")

app.include_router(token.router)
app.include_router(voice.router)
app.include_router(webhooks.router)
app.include_router(calls.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def index():
    return FileResponse("app/static/index.html")
