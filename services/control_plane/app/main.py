from fastapi import FastAPI
from .database import engine, Base
from .api.routes import sources, serving
import os
from fastapi.staticfiles import StaticFiles

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Streamo Control Plane API",
    description="API for managing Streamo Data Engineering Pipelines",
    version="0.1.0"
)

app.include_router(sources.router, prefix="/api/v1/sources", tags=["sources"])
app.include_router(serving.router, prefix="/api/v1/serving", tags=["Serving"])

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "streamo-control-plane"}

frontend_path = "/frontend" if os.path.exists("/frontend") else os.path.join(os.path.dirname(__file__), "../../../frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
