import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from routes.upload import router as upload_router
from routes.analyze import router as analyze_router


app = FastAPI(
    title="ResearchLens API",
    description="AI-powered research paper summarizer and visual analytics system.",
    version="1.0.0",
)


# Dynamic CORS configuration
cors_env = os.getenv("CORS_ORIGINS", "*").strip()
if cors_env == "*":
    allow_origins = ["*"]
    allow_credentials = False
else:
    allow_origins = [o.strip() for o in cors_env.split(",") if o.strip()]
    for local in ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]:
        if local not in allow_origins:
            allow_origins.append(local)
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register routes
app.include_router(upload_router)
app.include_router(analyze_router)


@app.get("/api/health")
async def health_check():
    return {
        "success": True,
        "status": "ResearchLens backend is running"
    }


# Static frontend hosting for unified deployments (Docker, Render, etc.)
frontend_dist_candidates = [
    Path(__file__).resolve().parent / "dist",
    Path(__file__).resolve().parent.parent / "frontend" / "dist",
]

frontend_dist = next((p for p in frontend_dist_candidates if p.exists() and (p / "index.html").exists()), None)

if frontend_dist:
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        requested_file = frontend_dist / full_path
        if requested_file.is_file():
            return FileResponse(requested_file)
        return FileResponse(frontend_dist / "index.html")