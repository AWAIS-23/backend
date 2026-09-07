---
title: Rising Skills Backend
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

# Rising Skills — Backend

Production-grade FastAPI backend for **Rising Skills** — A Skills-to-Opportunity platform.

## Architecture

The backend is built as a **Modular Monolith** with strict layered separation:
- **API Layer (`app/api/v1/`)**: HTTP endpoints, schema validation, zero business logic.
- **Dependencies (`app/dependencies/`)**: Supabase JWT authentication, RBAC authorization guards, DB session injection.
- **Services (`app/services/`)**: Core domain rules, assessment scoring, deterministic matching.
- **Repositories (`app/repositories/`)**: Data-access contracts isolating database operations.
- **Integrations (`app/integrations/`)**: Supabase GoTrue Auth, Groq AI (Pydantic validated).

## Local Development Setup

1. **Create and Activate Virtual Environment**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   ```

2. **Install Dependencies**:
   ```bash
   pip install -e ".[dev,ai]"
   ```

3. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials
   ```

4. **Run Database Migrations**:
   ```bash
   alembic upgrade head
   ```

5. **Start Development Server**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

6. **Run Tests**:
   ```bash
   pytest
   ```

## Docker Deployment

Build and run the backend from the `Backend` directory:

```bash
docker build -t rising-skills-backend .
docker run --env-file .env -p 7860:7860 rising-skills-backend
```

The container listens on the platform-provided `PORT` value and falls back to
`7860` for Hugging Face Spaces. The health check is available at `/health`.

### Vercel Testing

For a card-free test deployment, create a Vercel project with `Backend` as the
project root. Vercel uses `api/index.py` and `vercel.json` to expose this
FastAPI application. Add the same Supabase environment variables listed above,
then deploy with:

```bash
npx vercel --prod
```

Test the deployed API at `/health` and `/api/v1/health`.

### Render

The repository includes `../render.yaml`, configured to deploy the `Backend`
branch on Render's **Free** web service. In Render, choose **Blueprint** and
connect this repository. Add the secret environment variables requested by the
manifest, then run the database migrations once:

```bash
alembic upgrade head
```

Use the same `DIRECT_DATABASE_URL` and `DATABASE_URL` values as the deployed
service when running migrations.
