"""Standalone loopback-only server for the read-only AlientAI model monitor."""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from alientai_v2.model_monitor import router as model_monitor_router


app = FastAPI(
    title="AlientAI Model Intelligence Monitor",
    docs_url=None,
    redoc_url=None,
)
app.include_router(model_monitor_router)


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/v2/models")


@app.get("/health", include_in_schema=False)
def health():
    return {
        "status": "ok",
        "app": "AlientAI Model Intelligence Monitor",
        "research_only": True,
        "execution_enabled": False,
    }
