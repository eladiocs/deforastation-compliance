from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import analyses, parcels

# Tables are created/versioned via Alembic (`alembic upgrade head`), not create_all.

app = FastAPI(title="inmuebles-risk", version="0.1.0")

allowed_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(parcels.router)
app.include_router(analyses.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
