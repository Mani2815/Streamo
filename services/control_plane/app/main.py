from fastapi import FastAPI
from .database import engine, Base
from .api.routes import sources, serving
import os
from fastapi.staticfiles import StaticFiles

# Create database tables
if engine:
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Warning: Could not create database tables. DB might be unavailable. {e}")

app = FastAPI(
    title="Streamo Control Plane API",
    description="API for managing Streamo Data Engineering Pipelines",
    version="0.1.0"
)

app.include_router(sources.router, prefix="/api/v1/sources", tags=["sources"])
app.include_router(serving.router, prefix="/api/v1/serving", tags=["Serving"])

@app.get("/health")
def health_check():
    from sqlalchemy import text
    from .database import engine
    from confluent_kafka.admin import AdminClient
    from fastapi.responses import JSONResponse
    
    db_status = "disconnected"
    if engine:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {str(e)}"

    kafka_status = "disconnected"
    
    # --- START DIAGNOSTICS ---
    render_kafka = os.environ.get("RENDER_KAFKA_URL")
    bootstrap_kafka = os.environ.get("KAFKA_BOOTSTRAP_SERVERS")
    
    config_source = "DEFAULT"
    kafka_servers = "streamo-kafka:9092"
    
    if render_kafka:
        config_source = "RENDER_KAFKA_URL"
        kafka_servers = render_kafka
    elif bootstrap_kafka:
        config_source = "KAFKA_BOOTSTRAP_SERVERS"
        kafka_servers = bootstrap_kafka
        
    print(f"KAFKA CONFIG SOURCE: {config_source}", flush=True)
    
    # Parse host and port safely
    host = kafka_servers
    port = "unknown"
    if ":" in kafka_servers:
        parts = kafka_servers.rsplit(":", 1)
        host = parts[0]
        port = parts[1]
        
    print(f"KAFKA HOST: {host}", flush=True)
    print(f"KAFKA PORT: {port}", flush=True)
    # --- END DIAGNOSTICS ---

    if kafka_servers:
        try:
            admin = AdminClient({'bootstrap.servers': kafka_servers})
            md = admin.list_topics(timeout=3)
            if md:
                kafka_status = "connected"
        except Exception as e:
            kafka_status = f"error: {str(e)}"
            
    status_code = 200 if db_status == "connected" and kafka_status == "connected" else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if status_code == 200 else "error",
            "service": "streamo-control-plane", 
            "database": db_status,
            "kafka": kafka_status
        }
    )

frontend_path = "/frontend" if os.path.exists("/frontend") else os.path.join(os.path.dirname(__file__), "../../../frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
