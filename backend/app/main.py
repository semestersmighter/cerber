"""Point d'entrée de l'API CERBER."""
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from psycopg_pool import PoolTimeout

from . import config, db
from .routers import access, admin, auth, me, tax


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.open_pool()
    yield
    db.close_pool()


app = FastAPI(title="CERBER", description="Portail d'authentification DGFIP", lifespan=lifespan,
              docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)

# Pas de CORS : le front et l'API sont servis sur la même origine (nginx fait le proxy /api).

# Refuse les requêtes dont l'en-tête Host n'est pas dans ALLOWED_HOSTS (400)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.ALLOWED_HOSTS)

app.include_router(auth.router)
app.include_router(me.router)
app.include_router(access.router)
app.include_router(admin.router)
app.include_router(tax.router)


FIELD_LABELS = {
    "nif": "NIF (13 chiffres)", "code": "code (6 chiffres)", "email": "email",
    "url": "URL (chemin comme /intranet/, ou https://)", "slug": "identifiant (minuscules, chiffres, tirets)",
    "role_ids": "rôles", "name": "nom", "address": "adresse", "rate": "taux (0 à 60 %, une décimale)",
}


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    """Message lisible plutôt que la structure brute de Pydantic."""
    fields = []
    for err in exc.errors():
        field = str(err["loc"][-1]) if err.get("loc") else ""
        label = FIELD_LABELS.get(field, field)
        if label and label not in fields:
            fields.append(label)
    return JSONResponse({"detail": "Champ invalide : " + ", ".join(fields)}, status_code=422)


@app.exception_handler(psycopg.OperationalError)
@app.exception_handler(PoolTimeout)
async def database_unavailable(request: Request, exc: Exception):
    return JSONResponse({"detail": "Base de données indisponible"}, status_code=503)


@app.get("/api/health", tags=["santé"])
def health():
    db.fetch_one("SELECT 1")
    return {"status": "ok"}
