from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.routers.chat import router as chat_router
from backend.app.routers.ai import router as ai_router
from backend.app.routers.phases import router as phases_router
from backend.app.routers.research import router as research_router
from backend.app.routers.scoring import router as scoring_router
from backend.app.routers.ideas import router as ideas_router
from backend.app.routers.relationships import router as relationships_router
from backend.app.routers.reports import router as reports_router
from backend.app.routers.memory import router as memory_router
from backend.app.routers.build import router as build_router
from backend.app.routers.github import router as github_router
from backend.app.routers.projects import router as projects_router
from backend.app.routers.worker import router as worker_router


app = FastAPI(title="Idea Refinery")

STATIC_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"
frontend_static = StaticFiles(directory=STATIC_DIR, check_dir=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_router)
app.include_router(chat_router)
app.include_router(phases_router)
app.include_router(research_router)
app.include_router(scoring_router)
app.include_router(ideas_router)
app.include_router(relationships_router)
app.include_router(reports_router)
app.include_router(memory_router)
app.include_router(build_router)
app.include_router(github_router)
app.include_router(projects_router)
app.include_router(worker_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")

    file_path = STATIC_DIR / full_path if full_path else STATIC_DIR / "index.html"
    if file_path.is_file():
        return FileResponse(file_path)
    return FileResponse(STATIC_DIR / "index.html")
