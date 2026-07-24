from fastapi import FastAPI

from app.database.base import Base
from app.database.session import engine
from fastapi.middleware.cors import CORSMiddleware
# IMPORTANT
from app.database.models.event import Event
from app.api.dashboard import router as dashboard_router
from app.api.events import router as event_router
from app.api.attention import router as attention_router
from app.api.health import router as health_router
from fastapi.staticfiles import StaticFiles
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Attention Drift Agent"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount(
    "/ui",
    StaticFiles(
        directory="dashboard"
    ),                                      
    name="ui"
)
app.include_router(event_router)
app.include_router(attention_router)
app.include_router(health_router)
app.include_router(dashboard_router)