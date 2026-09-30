"""Journal des événements d'authentification (consultable par l'administrateur)."""
from fastapi import Request

from . import db

# Types d'événements enregistrés
LOGIN = "LOGIN"                    # mot de passe vérifié (succès/échec)
ACCOUNT_LOCKED = "ACCOUNT_LOCKED"  # verrouillage après trop d'échecs
MFA = "MFA"                        # code TOTP vérifié (succès/échec)
TOTP_ENROLLED = "TOTP_ENROLLED"    # nouvelle application TOTP enregistrée
TOKEN_RENEWED = "TOKEN_RENEWED"    # renouvellement du jeton de session
LOGOUT = "LOGOUT"
PASSWORD_RESET = "PASSWORD_RESET"  # demande de réinitialisation (mot de passe oublié)
PASSWORD_CHANGED = "PASSWORD_CHANGED"
PROFILE_UPDATED = "PROFILE_UPDATED"
ACCESS_CHECK = "ACCESS_CHECK"      # contrôle d'accès à une ressource
ADMIN = "ADMIN"                    # action d'administration

TYPES = [
    LOGIN, ACCOUNT_LOCKED, MFA, TOTP_ENROLLED, TOKEN_RENEWED, LOGOUT,
    PASSWORD_RESET, PASSWORD_CHANGED, PROFILE_UPDATED, ACCESS_CHECK, ADMIN,
]


def client_ip(request: Request) -> str | None:
    # nginx transmet l'IP réelle du client dans X-Real-IP
    return request.headers.get("x-real-ip") or (request.client.host if request.client else None)


def log(request: Request, type_: str, success: bool, nif: str | None = None, detail: str | None = None):
    db.execute(
        'INSERT INTO "AuthEvent" ("nif", "type", "success", "ip", "detail") VALUES (%s, %s, %s, %s, %s)',
        (nif, type_, success, client_ip(request), (detail or "")[:255] or None),
    )
