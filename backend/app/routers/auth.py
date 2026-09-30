"""Authentification : mot de passe -> code TOTP -> jeton de session.

Parcours :
  1. POST /api/auth/login        NIF + mot de passe  -> cookie cerber_mfa (5 min)
  2. GET  /api/auth/totp/setup   (1re connexion) QR code à scanner
  3. POST /api/auth/mfa          code TOTP           -> cookie cerber_session
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from .. import config, db, events
from ..deps import CurrentUser, clear_cookie, current_user, set_cookie
from ..schemas import CodeIn, ForgotPasswordIn, LoginIn
from ..security import (
    hash_password, hash_token, new_token, new_totp_secret, password_problems,
    totp_qr_svg, totp_uri, verify_password, verify_totp,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

INVALID = "Identifiants invalides"
LOCKED = f"Compte verrouillé après {config.MAX_LOGIN_ATTEMPTS} échecs. Réessayez dans {config.LOCK_MINUTES} minutes."


# ---------- Utilitaires ----------

def _get_user(nif: str):
    # "locked" est calculé par PostgreSQL pour éviter tout problème de fuseau horaire
    return db.fetch_one(
        '''
        SELECT "nif", "email", "passwordHash", "nbTry", "lockDate",
               "totpSecret", "totpPendingSecret", "totpLastStep",
               ("lockDate" IS NOT NULL AND "lockDate" > now() - make_interval(mins => %s)) AS "locked"
        FROM "User" WHERE "nif" = %s
        ''',
        (config.LOCK_MINUTES, nif),
    )


def _clear_expired_lock(user):
    """Verrouillage expiré : le compteur repart de zéro."""
    if user["lockDate"] is not None and not user["locked"]:
        db.execute('UPDATE "User" SET "nbTry" = 0, "lockDate" = NULL WHERE "nif" = %s', (user["nif"],))
        user["nbTry"] = 0


def _register_failure(request: Request, nif: str) -> bool:
    """Incrémente le compteur d'échecs ; renvoie True si le compte vient d'être verrouillé."""
    row = db.execute(
        '''
        UPDATE "User"
        SET "nbTry" = "nbTry" + 1,
            "lockDate" = CASE WHEN "nbTry" + 1 >= %s THEN now() ELSE "lockDate" END
        WHERE "nif" = %s
        RETURNING "nbTry"
        ''',
        (config.MAX_LOGIN_ATTEMPTS, nif),
    )
    just_locked = row is not None and row["nbTry"] == config.MAX_LOGIN_ATTEMPTS
    if just_locked:
        events.log(request, events.ACCOUNT_LOCKED, True, nif)
    return just_locked


def _challenge_user(request: Request):
    """Utilisateur ayant validé son mot de passe mais pas encore son code TOTP."""
    token = request.cookies.get(config.MFA_COOKIE)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Reconnectez-vous")
    row = db.fetch_one(
        'SELECT "nif" FROM "MfaChallenge" WHERE "tokenHash" = %s AND "expireAt" > now()',
        (hash_token(token),),
    )
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Délai dépassé, reconnectez-vous")
    return _get_user(row["nif"])


def _open_session(response: Response, nif: str) -> str:
    token, token_hash = new_token()
    with db.transaction() as conn:
        conn.execute('DELETE FROM "Session" WHERE "expireAt" <= now()')
        conn.execute(
            'INSERT INTO "Session" ("tokenHash", "nif", "expireAt") '
            'VALUES (%s, %s, now() + make_interval(mins => %s))',
            (token_hash, nif, config.SESSION_MINUTES),
        )
    set_cookie(response, config.SESSION_COOKIE, token, config.SESSION_MINUTES)
    return token


# ---------- Étape 1 : mot de passe ----------

@router.post("/login")
def login(body: LoginIn, request: Request, response: Response):
    user = _get_user(body.nif)

    if user is None:
        verify_password(None, body.password)  # temps de réponse constant
        events.log(request, events.LOGIN, False, None, f"NIF inconnu {body.nif}")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID)

    if user["locked"]:
        events.log(request, events.LOGIN, False, user["nif"], "compte verrouillé")
        raise HTTPException(status.HTTP_423_LOCKED, LOCKED)

    _clear_expired_lock(user)

    if not verify_password(user["passwordHash"], body.password):
        events.log(request, events.LOGIN, False, user["nif"], "mot de passe incorrect")
        if _register_failure(request, user["nif"]):
            raise HTTPException(status.HTTP_423_LOCKED, LOCKED)
        # Même message que pour un NIF inconnu : on ne révèle pas quels comptes existent
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID)

    # Le compteur d'échecs n'est remis à zéro qu'après le code TOTP :
    # connaître le mot de passe ne permet pas de tenter des codes à l'infini.
    token, token_hash = new_token()
    with db.transaction() as conn:
        conn.execute('DELETE FROM "MfaChallenge" WHERE "nif" = %s OR "expireAt" <= now()', (user["nif"],))
        conn.execute(
            'INSERT INTO "MfaChallenge" ("tokenHash", "nif", "expireAt") '
            'VALUES (%s, %s, now() + make_interval(mins => %s))',
            (token_hash, user["nif"], config.MFA_CHALLENGE_MINUTES),
        )
    set_cookie(response, config.MFA_COOKIE, token, config.MFA_CHALLENGE_MINUTES)
    events.log(request, events.LOGIN, True, user["nif"])
    return {"totp_enrolled": user["totpSecret"] is not None}


# ---------- Étape 2 (1re connexion) : enrôlement TOTP ----------

@router.get("/totp/setup")
def totp_setup(request: Request):
    user = _challenge_user(request)
    if user["totpSecret"] is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Application TOTP déjà enregistrée")
    secret = user["totpPendingSecret"]
    if secret is None:
        secret = new_totp_secret()
        db.execute('UPDATE "User" SET "totpPendingSecret" = %s WHERE "nif" = %s', (secret, user["nif"]))
    uri = totp_uri(secret, user["email"])
    return {"secret": secret, "qr_svg": totp_qr_svg(uri)}


# ---------- Étape 3 : code TOTP ----------

@router.post("/mfa")
def mfa(body: CodeIn, request: Request, response: Response):
    user = _challenge_user(request)

    if user["locked"]:
        raise HTTPException(status.HTTP_423_LOCKED, LOCKED)

    enrolling = user["totpSecret"] is None
    secret = user["totpPendingSecret"] if enrolling else user["totpSecret"]
    if secret is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Aucune application TOTP à vérifier")

    step = verify_totp(secret, body.code, user["totpLastStep"])
    if step is None:
        events.log(request, events.MFA, False, user["nif"], "code TOTP invalide")
        if _register_failure(request, user["nif"]):
            db.execute('DELETE FROM "MfaChallenge" WHERE "nif" = %s', (user["nif"],))
            clear_cookie(response, config.MFA_COOKIE)
            raise HTTPException(status.HTTP_423_LOCKED, LOCKED)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Code incorrect")

    with db.transaction() as conn:
        conn.execute(
            '''
            UPDATE "User" SET "nbTry" = 0, "lockDate" = NULL, "totpLastStep" = %s,
                   "totpSecret" = %s, "totpPendingSecret" = NULL
            WHERE "nif" = %s
            ''',
            (step, secret, user["nif"]),
        )
        conn.execute('DELETE FROM "MfaChallenge" WHERE "nif" = %s', (user["nif"],))

    if enrolling:
        events.log(request, events.TOTP_ENROLLED, True, user["nif"], "première connexion")
    events.log(request, events.MFA, True, user["nif"])

    clear_cookie(response, config.MFA_COOKIE)
    _open_session(response, user["nif"])
    return {"message": "Connexion réussie"}


# ---------- Session ----------

@router.post("/refresh")
def refresh(request: Request, response: Response, user: CurrentUser = Depends(current_user)):
    """Renouvelle le jeton : l'ancien est invalidé, un nouveau est émis."""
    db.execute('DELETE FROM "Session" WHERE "tokenHash" = %s', (user.token_hash,))
    _open_session(response, user.nif)
    events.log(request, events.TOKEN_RENEWED, True, user.nif)
    return {"expires_in": config.SESSION_MINUTES * 60}


@router.post("/logout")
def logout(request: Request, response: Response, user: CurrentUser = Depends(current_user)):
    db.execute('DELETE FROM "Session" WHERE "tokenHash" = %s', (user.token_hash,))
    clear_cookie(response, config.SESSION_COOKIE)
    events.log(request, events.LOGOUT, True, user.nif)
    return {"message": "Déconnecté"}


# ---------- Mot de passe oublié (NIF + code TOTP) ----------

@router.post("/password/forgot")
def forgot_password(body: ForgotPasswordIn, request: Request):
    problems = password_problems(body.new_password)
    if problems:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Le mot de passe doit contenir " + ", ".join(problems))

    user = _get_user(body.nif)
    if user is None or user["totpSecret"] is None:
        events.log(request, events.PASSWORD_RESET, False, user and user["nif"], "compte inconnu ou sans TOTP")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "NIF ou code incorrect")
    if user["locked"]:
        events.log(request, events.PASSWORD_RESET, False, user["nif"], "compte verrouillé")
        raise HTTPException(status.HTTP_423_LOCKED, LOCKED)
    _clear_expired_lock(user)

    step = verify_totp(user["totpSecret"], body.code, user["totpLastStep"])
    if step is None:
        events.log(request, events.PASSWORD_RESET, False, user["nif"], "code TOTP invalide")
        if _register_failure(request, user["nif"]):
            raise HTTPException(status.HTTP_423_LOCKED, LOCKED)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "NIF ou code incorrect")

    with db.transaction() as conn:
        conn.execute(
            'UPDATE "User" SET "passwordHash" = %s, "nbTry" = 0, "lockDate" = NULL, "totpLastStep" = %s WHERE "nif" = %s',
            (hash_password(body.new_password), step, user["nif"]),
        )
        # Toutes les sessions ouvertes sont fermées
        conn.execute('DELETE FROM "Session" WHERE "nif" = %s', (user["nif"],))
    events.log(request, events.PASSWORD_RESET, True, user["nif"])
    return {"message": "Mot de passe réinitialisé"}
