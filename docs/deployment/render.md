# Render Deployment Guide

Streamo is designed for full-stack data engineering locally using Docker Compose, but you can deploy its public-facing web application and API (FastAPI Control Plane + UI) to Render for demonstration purposes.

## 1. Architecture

The Render deployment is **only the web layer**. It consists of:
- **FastAPI Control Plane**: The Python API serving data to the dashboard.
- **Frontend**: The Vanilla JS web interface served statically by FastAPI.

**NOT Deployed on Render:**
Kafka, Spark, PostgreSQL, Airflow, MinIO, and Grafana remain in your local or VM Docker Compose environment. The Render web service hosts the web application layer to serve the public Streamo Demo, and it must not be confused with the full-stack architecture.

## 2. Prerequisites
- A Render account.
- An externally accessible PostgreSQL database (e.g., Supabase, Neon, AWS RDS, or Render Managed Postgres). Note: `postgres` from the local docker-compose will not work.

## 3. Render Service Configuration

We have provided a `render.yaml` Blueprint to make deployment easier.
Alternatively, deploy manually via the Render Dashboard using these settings:

- **Repository**: Mani2815/Streamo
- **Branch**: main
- **Root Directory**: *(leave blank or `/`)*
  - **CRITICAL**: Do NOT use `services/control-plane` or `services/control_plane` as the Root Directory. The build context must be the repository root to access both `services/control_plane` and `frontend`.
- **Runtime**: Docker
- **Dockerfile Path**: `./Dockerfile.render`
- **Health Check Path**: `/health`

## 4. Environment Variables

The following environment variables should be configured in your Render dashboard:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | No* | The connection string for your managed PostgreSQL database. Format: `postgresql://user:password@host:port/dbname`.<br><br>\* *Note: The application will start without it, but the dashboard will not be able to display any data. Do not use local Docker credentials.* |

## 5. Build Process & Dockerfile
The repository contains `./Dockerfile.render` located at the root. This Dockerfile:
- Uses `python:3.11-slim`.
- Sets the context to the repository root.
- Installs FastAPI dependencies from `services/control_plane/requirements.txt`.
- Copies the `services/control_plane/app/` source code.
- Copies the `frontend/` to the absolute `/frontend` path so it is correctly served as static files by FastAPI.

## 6. Deployment Steps
1. Create a new **Web Service** in Render.
2. Connect your Streamo GitHub repository.
3. Apply the **Render Service Configuration** specified in Section 3.
4. Add the `DATABASE_URL` under Environment Variables.
5. Click **Create Web Service**.

The start command used by the container is:
```bash
sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
```
This correctly binds to Render's injected `$PORT` environment variable and `0.0.0.0`.

## 7. Troubleshooting
- **Data Not Loading**: If the web app is up but data isn't loading, ensure `DATABASE_URL` is set correctly and the database is reachable.
- **Path Errors**: If the deployment fails to build, verify that your Root Directory is blank. Do not set it to the control plane directory.

## 8. External Service Requirements
- **PostgreSQL**: Required to actually populate the dashboard with data.
- **Kafka / Spark / MinIO**: These are NOT required by the web application. The FastAPI Control Plane is decoupled and will handle gracefully if these are not present.

## 9. Free-Tier Limitations
- **Spin Down**: If deploying on Render's Free tier, the web service will spin down after 15 minutes of inactivity. Subsequent requests will take up to 50 seconds to spin the instance back up. This is not a 24/7 uptime environment.
- **Read-Only Dashboard**: Without an external Kafka and Spark streaming environment constantly pushing data to your managed Postgres, the public dashboard will only show static, historical data injected previously. This is a portfolio/demo deployment, not a production-scale real-time processing cluster.
