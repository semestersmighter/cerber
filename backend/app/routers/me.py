"""Espace utilisateur : profil, mot de passe, application TOTP, ressources accessibles."""
import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request, status

from .. import db, events
from ..deps import CurrentUser, current_user
from ..schemas import ChangePasswordIn, CodeIn, PasswordIn, ProfileIn
from ..security import (
    hash_password, new_totp_secret, password_problems, totp_qr_svg, totp_uri,
    verify_password, verify_totp,
)

router = APIRouter(prefix="/api/me", tags=["utilisateur"])


@router.get("")
def me(user: CurrentUser = Depends(current_user)):
    row = db.fetch_one(
        '''
        SELECT u."nif", u."email", u."address", u."totpSecret" IS NOT NULL AS "totp_enabled",
               t."rate"::float8 AS "tax_rate"
        FROM "User" u LEFT JOIN "TaxRate" t ON t."nif" = u."nif"
        WHERE u."nif" = %s
        ''',
        (user.nif,),
    )
    return {**row, "roles": user.roles, "is_admin": user.is_admin}


@router.patch("")
def update_profile(body: ProfileIn, request: Request, user: CurrentUser = Depends(current_user)):
    try:
        db.execute(
            'UPDATE "User" SET "email" = %s, "address" = %s WHERE "nif" = %s',
            (body.email.strip(), body.address.strip(), user.nif),
        )
    except psycopg.errors.UniqueViolation:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cette adresse email est déjà utilisée")
    events.log(request, events.PROFILE_UPDATED, True, user.nif)
    return {"message": "Informations mises à jour"}


@router.post("/password")
def change_password(body: ChangePasswordIn, request: Request, user: CurrentUser = Depends(current_user)):
    row = db.fetch_one('SELECT "passwordHash" FROM "User" WHERE "nif" = %s', (user.nif,))
    if not verify_password(row["passwordHash"], body.current_password):
        events.log(request, events.PASSWORD_CHANGED, False, user.nif, "mot de passe actuel incorrect")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Mot de passe actuel incorrect")
    problems = password_problems(body.new_password)
    if problems:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Le mot de passe doit contenir " + ", ".join(problems))
    with db.transaction() as conn:
        conn.execute('UPDATE "User" SET "passwordHash" = %s WHERE "nif" = %s', (hash_password(body.new_password), user.nif))
        # Les autres sessions (autres appareils) sont fermées, la session courante est conservée
        conn.execute('DELETE FROM "Session" WHERE "nif" = %s AND "tokenHash" <> %s', (user.nif, user.token_hash))
    events.log(request, events.PASSWORD_CHANGED, True, user.nif)
    return {"message": "Mot de passe modifié"}


@router.post("/totp/renew")
def renew_totp(body: PasswordIn, request: Request, user: CurrentUser = Depends(current_user)):
    """Changement d'application TOTP (nouveau téléphone) : confirmé par le mot de passe."""
    row = db.fetch_one('SELECT "passwordHash" FROM "User" WHERE "nif" = %s', (user.nif,))
    if not verify_password(row["passwordHash"], body.password):
        events.log(request, events.TOTP_ENROLLED, False, user.nif, "mot de passe incorrect")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Mot de passe incorrect")
    secret = new_totp_secret()
    db.execute('UPDATE "User" SET "totpPendingSecret" = %s WHERE "nif" = %s', (secret, user.nif))
    return {"secret": secret, "qr_svg": totp_qr_svg(totp_uri(secret, user.email))}


@router.post("/totp/confirm")
def confirm_totp(body: CodeIn, request: Request, user: CurrentUser = Depends(current_user)):
    row = db.fetch_one('SELECT "totpPendingSecret" FROM "User" WHERE "nif" = %s', (user.nif,))
    secret = row["totpPendingSecret"]
    if secret is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Aucun changement d'application en cours")
    step = verify_totp(secret, body.code, 0)
    if step is None:
        events.log(request, events.TOTP_ENROLLED, False, user.nif, "code de confirmation invalide")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Code incorrect")
    db.execute(
        'UPDATE "User" SET "totpSecret" = %s, "totpPendingSecret" = NULL, "totpLastStep" = %s WHERE "nif" = %s',
        (secret, step, user.nif),
    )
    events.log(request, events.TOTP_ENROLLED, True, user.nif, "changement d'application")
    return {"message": "Nouvelle application TOTP enregistrée"}


@router.get("/resources")
def my_resources(user: CurrentUser = Depends(current_user)):
    return db.fetch_all(
        '''
        SELECT DISTINCT r."slug", r."name", r."url"
        FROM "Resource" r
        JOIN "ResourceRole" rr ON rr."resourceID" = r."resourceID"
        JOIN "UserRole" ur ON ur."roleID" = rr."roleID"
        WHERE ur."nif" = %s
        ORDER BY r."name"
        ''',
        (user.nif,),
    )
