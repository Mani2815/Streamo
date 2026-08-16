# Render Deployment Guide

Streamo is designed for full-stack data engineering locally using Docker Compose, but you can deploy its public-facing web application and API (FastAPI Control Plane + UI) to Render for demonstration purposes.

## Architecture

- **Render**: FastAPI Control Plane + Streamo UI (Static files).
- **Supabase**: Persistent PostgreSQL Database backing the public web application.
- **Docker Compose (Local)**: The complete Kafka, Spark, Airflow, MinIO, and Grafana environment for full data engineering tasks.

**NOT Deployed on Render:**
Kafka, Spark, PostgreSQL, Airflow, MinIO, and Grafana remain in your local Docker Compose environment. The Render web service hosts the web application layer to serve the public Streamo Demo, and it must not be confused with the full-stack architecture.

## Supabase PostgreSQL

To run the application publicly without local Docker, you must provide a managed PostgreSQL database. Supabase is recommended because it perfectly matches Streamo's PostgreSQL requirements.

1. Create a Supabase project and obtain the database connection string.
2. The format is standard Postgres: `postgresql://[USER]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres`
3. Credentials must be provided entirely through the `DATABASE_URL` environment variable. 
4. Do NOT hardcode credentials in source code. 
5. Local Docker PostgreSQL remains unchanged and continues to use the existing `docker-compose.yml`.

## Render Environment Variables

The following environment variables should be configured in your Render dashboard:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | The connection string for your managed PostgreSQL database (e.g., Supabase). Do not use local Docker credentials. |

## Build Process & Dockerfile
The repository contains `./Dockerfile.render` located at the root. This Dockerfile:
- Uses `python:3.11-slim`.
- Sets the context to the repository root.
- Installs FastAPI dependencies from `services/control_plane/requirements.txt`.
- Copies the `services/control_plane/app/` source code.
- Copies the `frontend/` to the absolute `/frontend` path so it is correctly served as static files by FastAPI.

## Deployment Steps
1. Create a new **Web Service** in Render.
2. Connect your Streamo GitHub repository.
3. Apply the **Render Service Configuration** specified below.
4. Add the `DATABASE_URL` under Environment Variables.
5. Click **Create Web Service**.

**Render Service Configuration:**
- **Repository**: Mani2815/Streamo
- **Branch**: main
- **Root Directory**: *(leave blank or `/`)*
- **Runtime**: Docker
- **Dockerfile Path**: `./Dockerfile.render`
- **Health Check Path**: `/health`

## Seeding Demo Data
Because the Render deployment is a read-only UI without a live Kafka/Spark processing cluster, the dashboard will initially appear completely empty. To populate the Supabase database with sample data for demonstration:

1. Copy your Supabase connection string.
2. Locally, run the safe seed script:
   ```bash
   export DATABASE_URL="postgresql://[USER]:[PASSWORD]@[HOST]:[PORT]/[DB]"
   python3 scripts/seed_demo_data.py
   ```
   This script will safely inject clearly labeled demo data so the public UI functions properly.

## Troubleshooting
- **Data Not Loading**: If the web app is up but data isn't loading, ensure `DATABASE_URL` is set correctly and the database is reachable.
- **Path Errors**: If the deployment fails to build, verify that your Root Directory is blank. Do not set it to the control plane directory.

## Free-Tier Limitations
- **Spin Down**: If deploying on Render's Free tier, the web service will spin down after 15 minutes of inactivity. Subsequent requests will take up to 50 seconds to spin the instance back up. This is not a 24/7 uptime environment.
- **Read-Only Dashboard**: Without an external Kafka and Spark streaming environment constantly pushing data to your managed Postgres, the public dashboard will only show static, historical data (either injected via the seed script or left over from previous local runs synced to the cloud). This is a portfolio/demo deployment, not a production-scale real-time processing cluster.
