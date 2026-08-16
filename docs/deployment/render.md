# Render Deployment Guide

Streamo is designed for full-stack data engineering locally, but you can deploy its public-facing web dashboard and API (Control Plane) to Render for demonstration purposes.

## 1. Architecture

The Render deployment is **only the web layer**. It consists of:
- **FastAPI Control Plane**: The Python API serving data to the dashboard.
- **Frontend**: The Vanilla JS web interface served statically by FastAPI.

**NOT Deployed on Render:**
Kafka, Spark, Airflow, MinIO, and Grafana remain in your local Docker Compose environment. The Render web service cannot run these distributed systems.

## 2. Prerequisites
- A Render account.
- An externally accessible PostgreSQL database (e.g., Supabase, Neon, AWS RDS, or Render Managed Postgres).

## 3. Render Setup

We have provided a `render.yaml` Blueprint to make deployment one-click.
Alternatively, deploy manually via the Render Dashboard:

1. Create a new **Web Service**.
2. Connect your Streamo repository.
3. Select **Docker** as the Environment.
4. Set the **Dockerfile Path** to `Dockerfile.render`.
5. Set the Health Check path to `/health`.

## 4. Environment Variables

The following environment variables must be configured in your Render dashboard:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | **Yes** | The connection string for your managed PostgreSQL database. FastAPI requires this to boot and create tables. Format: `postgresql://user:password@host:port/dbname` |
| `KAFKA_BOOTSTRAP_SERVERS` | No* | URL of an external Kafka cluster. *Note: Only required if you intend to click "Add Source" from the public dashboard. The dashboard analytics and quality views will work without it.* |

## 5. Build Configuration
The repository contains `Dockerfile.render`. This Dockerfile:
- Installs FastAPI dependencies.
- Copies the `control_plane` source code.
- Copies the `frontend` to the absolute `/frontend` path so it matches the expected local mount behavior.

## 6. Start Configuration
The `Dockerfile.render` uses the following start command:
```bash
sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
```
This correctly binds to Render's injected `$PORT` environment variable.

## 7. Health Check
Render will automatically ping the `GET /health` endpoint. If it returns HTTP 200 `{"status": "ok", "service": "streamo-control-plane"}`, the deployment will be marked as live.

## 8. Database Configuration
**Do not** point `DATABASE_URL` to `postgres:5432` or `localhost`. It must be a publicly accessible database URI. 

## 9. Frontend/API Configuration
The frontend uses relative paths (`/api/v1/sources`). No CORS configuration or environment variables are needed for the frontend. It will seamlessly communicate with the FastAPI backend regardless of the deployed domain.

## 10. Troubleshooting
- **Deploy fails during startup**: Check the deployment logs. If it says `sqlalchemy.exc.OperationalError`, your `DATABASE_URL` is either missing or unreachable.
- **"Add Source" button fails**: Ensure `KAFKA_BOOTSTRAP_SERVERS` is set and reachable, as adding a source attempts to create a Kafka topic.

## 11. Free-Tier Limitations
- **Spin Down**: If deploying on Render's Free tier, the web service will spin down after 15 minutes of inactivity. Subsequent requests will take up to 50 seconds to spin the instance back up.
- **Read-Only Dashboard**: Without an external Kafka and Spark streaming environment constantly pushing data to your managed Postgres, the public dashboard will only show static, historical data injected previously.

## 12. Rollback/Redeployment
Render automatically redeploys on new commits to your connected branch. To rollback, navigate to your Render Dashboard -> "Deploys" -> select a previous successful deploy -> click "Rollback to this deploy".
