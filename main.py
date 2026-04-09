import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

APP_NAME = os.getenv("APP_NAME", "Emotional Journaling Assistant")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"[Startup] {APP_NAME} v{APP_VERSION} initializing...")

    from database import init_db
    init_db()
    logger.info("[Startup] Database initialized.")

    from sentiment import get_analyzer
    get_analyzer()
    logger.info("[Startup] Sentiment analyzer ready.")

    logger.info("[Startup] Service is ready.")
    yield

    # Shutdown
    logger.info("[Shutdown] Service shutting down.")


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="감정 일기를 작성하고 CBT 기반 심리 상담을 받으세요.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers import journal, analysis  # noqa: E402
app.include_router(journal.router)
app.include_router(analysis.router)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", tags=["Health"], include_in_schema=False)
def root():
    return FileResponse("static/index.html")


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host=host, port=port, reload=True)
