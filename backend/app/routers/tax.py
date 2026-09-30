"""Taux de prélèvement à la source des contribuables.

Réservé aux rôles autorisés sur la ressource « taux » (Agent DGFIP par défaut) :
l'administrateur choisit qui y a accès depuis la page Administration.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from .. import config, db, events
from ..deps import CurrentUser, require_resource
from ..schemas import TaxRateIn

# Créée une seule fois : FastAPI ne l'exécute alors qu'une fois par requête
require_tax_access = require_resource("taux")

router = APIRouter(prefix="/api/tax", tags=["impôts"], dependencies=[Depends(require_tax_access)])


@router.get("/taxpayers")
def list_taxpayers(nif: str = Query("", pattern=r"^\d{0,13}$", description="Filtrer par NIF (début)"),
                   agent: CurrentUser = Depends(require_tax_access)):
    return db.fetch_all(
        '''
        SELECT u."nif", u."email", t."rate"::float8 AS "rate", t."updatedBy" AS "updated_by", t."updatedAt" AS "updated_at"
        FROM "User" u
        JOIN "UserRole" ur ON ur."nif" = u."nif"
        JOIN "Role" r ON r."roleID" = ur."roleID" AND r."name" = %s
        LEFT JOIN "TaxRate" t ON t."nif" = u."nif"
        WHERE u."nif" <> %s AND u."nif" LIKE %s
        ORDER BY u."nif"
        LIMIT 200
        ''',
        (config.TAXPAYER_ROLE, agent.nif, nif + "%"),
    )


@router.put("/taxpayers/{nif}")
def update_rate(nif: str, body: TaxRateIn, request: Request, agent: CurrentUser = Depends(require_tax_access)):
    # Un agent ne modifie jamais son propre taux, même s'il est aussi contribuable
    if nif == agent.nif:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Vous ne pouvez pas modifier votre propre taux")
    taxpayer = db.fetch_one(
        '''
        SELECT 1 FROM "UserRole" ur JOIN "Role" r ON r."roleID" = ur."roleID"
        WHERE ur."nif" = %s AND r."name" = %s
        ''',
        (nif, config.TAXPAYER_ROLE),
    )
    if taxpayer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contribuable introuvable")

    old = db.fetch_one('SELECT "rate" FROM "TaxRate" WHERE "nif" = %s', (nif,))
    db.execute(
        '''
        INSERT INTO "TaxRate" ("nif", "rate", "updatedBy") VALUES (%s, %s, %s)
        ON CONFLICT ("nif") DO UPDATE SET "rate" = EXCLUDED."rate", "updatedBy" = EXCLUDED."updatedBy", "updatedAt" = now()
        ''',
        (nif, body.rate, agent.nif),
    )
    before = f"{old['rate']} %" if old else "aucun"
    events.log(request, events.TAX_RATE, True, agent.nif, f"contribuable {nif} : {before} -> {body.rate} %")
    return {"message": "Taux mis à jour", "nif": nif, "rate": float(body.rate)}
