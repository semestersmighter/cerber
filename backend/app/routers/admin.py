"""Administration : comptes, ressources, droits d'accès par rôle, journal."""
import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from .. import config, db, events
from ..deps import CurrentUser, require_admin
from ..schemas import ResourceIn, RoleIdsIn, UserCreateIn
from ..security import hash_password, password_problems

router = APIRouter(prefix="/api/admin", tags=["administration"], dependencies=[Depends(require_admin)])


# ---------- Rôles ----------

@router.get("/roles")
def list_roles():
    return db.fetch_all('SELECT "roleID" AS "id", "name" FROM "Role" ORDER BY "roleID"')


# ---------- Comptes ----------

@router.get("/users")
def list_users():
    return db.fetch_all(
        '''
        SELECT u."nif", u."email", u."address",
               u."totpSecret" IS NOT NULL AS "totp_enabled",
               (u."lockDate" IS NOT NULL AND u."lockDate" > now() - make_interval(mins => %s)) AS "locked",
               COALESCE(array_agg(r."name" ORDER BY r."name") FILTER (WHERE r."name" IS NOT NULL), '{}') AS "roles"
        FROM "User" u
        LEFT JOIN "UserRole" ur ON ur."nif" = u."nif"
        LEFT JOIN "Role" r ON r."roleID" = ur."roleID"
        GROUP BY u."nif"
        ORDER BY u."nif"
        ''',
        (config.LOCK_MINUTES,),
    )


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreateIn, request: Request, admin: CurrentUser = Depends(require_admin)):
    problems = password_problems(body.password)
    if problems:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Le mot de passe doit contenir " + ", ".join(problems))
    try:
        with db.transaction() as conn:
            conn.execute(
                'INSERT INTO "User" ("nif", "passwordHash", "email", "address") VALUES (%s, %s, %s, %s)',
                (body.nif, hash_password(body.password), body.email.strip(), body.address.strip()),
            )
            for role_id in set(body.role_ids):
                conn.execute('INSERT INTO "UserRole" ("nif", "roleID") VALUES (%s, %s)', (body.nif, role_id))
    except psycopg.errors.UniqueViolation:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ce NIF ou cet email existe déjà")
    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Rôle inconnu")
    events.log(request, events.ADMIN, True, admin.nif, f"création du compte {body.nif}")
    return {"message": "Compte créé", "nif": body.nif}


@router.delete("/users/{nif}")
def delete_user(nif: str, request: Request, admin: CurrentUser = Depends(require_admin)):
    if nif == admin.nif:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Vous ne pouvez pas supprimer votre propre compte")
    if db.execute('DELETE FROM "User" WHERE "nif" = %s RETURNING "nif"', (nif,)) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compte introuvable")
    events.log(request, events.ADMIN, True, admin.nif, f"suppression du compte {nif}")
    return {"message": "Compte supprimé"}


@router.post("/users/{nif}/unlock")
def unlock_user(nif: str, request: Request, admin: CurrentUser = Depends(require_admin)):
    if db.execute('UPDATE "User" SET "nbTry" = 0, "lockDate" = NULL WHERE "nif" = %s RETURNING "nif"', (nif,)) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compte introuvable")
    events.log(request, events.ADMIN, True, admin.nif, f"déverrouillage du compte {nif}")
    return {"message": "Compte déverrouillé"}


@router.post("/users/{nif}/reset-totp")
def reset_totp(nif: str, request: Request, admin: CurrentUser = Depends(require_admin)):
    """Téléphone perdu : l'utilisateur réenregistrera une application à sa prochaine connexion."""
    with db.transaction() as conn:
        row = conn.execute(
            'UPDATE "User" SET "totpSecret" = NULL, "totpPendingSecret" = NULL, "totpLastStep" = 0 '
            'WHERE "nif" = %s RETURNING "nif"',
            (nif,),
        ).fetchone()
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Compte introuvable")
        conn.execute('DELETE FROM "Session" WHERE "nif" = %s', (nif,))
    events.log(request, events.ADMIN, True, admin.nif, f"réinitialisation TOTP du compte {nif}")
    return {"message": "TOTP réinitialisé"}


# ---------- Ressources et droits d'accès ----------

@router.get("/resources")
def list_resources():
    return db.fetch_all(
        '''
        SELECT r."resourceID" AS "id", r."slug", r."name", r."url",
               COALESCE(array_agg(rr."roleID" ORDER BY rr."roleID") FILTER (WHERE rr."roleID" IS NOT NULL), '{}') AS "role_ids"
        FROM "Resource" r
        LEFT JOIN "ResourceRole" rr ON rr."resourceID" = r."resourceID"
        GROUP BY r."resourceID"
        ORDER BY r."name"
        '''
    )


def _set_resource_roles(conn, resource_id: int, role_ids: list[int]):
    conn.execute('DELETE FROM "ResourceRole" WHERE "resourceID" = %s', (resource_id,))
    for role_id in set(role_ids):
        conn.execute('INSERT INTO "ResourceRole" ("resourceID", "roleID") VALUES (%s, %s)', (resource_id, role_id))


@router.post("/resources", status_code=status.HTTP_201_CREATED)
def create_resource(body: ResourceIn, request: Request, admin: CurrentUser = Depends(require_admin)):
    try:
        with db.transaction() as conn:
            row = conn.execute(
                'INSERT INTO "Resource" ("slug", "name", "url") VALUES (%s, %s, %s) RETURNING "resourceID"',
                (body.slug, body.name.strip(), body.url),
            ).fetchone()
            _set_resource_roles(conn, row["resourceID"], body.role_ids)
    except psycopg.errors.UniqueViolation:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cet identifiant de ressource existe déjà")
    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Rôle inconnu")
    events.log(request, events.ADMIN, True, admin.nif, f"ajout de la ressource {body.slug}")
    return {"message": "Ressource ajoutée", "id": row["resourceID"]}


@router.put("/resources/{resource_id}/roles")
def update_resource_roles(resource_id: int, body: RoleIdsIn, request: Request, admin: CurrentUser = Depends(require_admin)):
    try:
        with db.transaction() as conn:
            row = conn.execute('SELECT "slug" FROM "Resource" WHERE "resourceID" = %s', (resource_id,)).fetchone()
            if row is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Ressource introuvable")
            _set_resource_roles(conn, resource_id, body.role_ids)
    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Rôle inconnu")
    events.log(request, events.ADMIN, True, admin.nif, f"droits de la ressource {row['slug']} : rôles {sorted(set(body.role_ids))}")
    return {"message": "Droits mis à jour"}


@router.delete("/resources/{resource_id}")
def delete_resource(resource_id: int, request: Request, admin: CurrentUser = Depends(require_admin)):
    row = db.execute('DELETE FROM "Resource" WHERE "resourceID" = %s RETURNING "slug"', (resource_id,))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ressource introuvable")
    events.log(request, events.ADMIN, True, admin.nif, f"suppression de la ressource {row['slug']}")
    return {"message": "Ressource supprimée"}


# ---------- Traçabilité ----------

@router.get("/events")
def list_events(
    type: str | None = Query(None, description="Filtrer par type d'événement"),
    nif: str | None = Query(None, description="Filtrer par NIF"),
    success: bool | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
):
    return {
        "types": events.TYPES,
        "events": db.fetch_all(
            '''
            SELECT "eventID" AS "id", "createdAt" AS "date", "nif", "type", "success", "ip", "detail"
            FROM "AuthEvent"
            WHERE (%(type)s::text IS NULL OR "type" = %(type)s)
              AND (%(nif)s::text IS NULL OR "nif" = %(nif)s)
              AND (%(success)s::boolean IS NULL OR "success" = %(success)s)
            ORDER BY "eventID" DESC
            LIMIT %(limit)s
            ''',
            {"type": type or None, "nif": nif or None, "success": success, "limit": limit},
        ),
    }
