"""FastAPI app entrypoint."""
import logging
import os

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


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
