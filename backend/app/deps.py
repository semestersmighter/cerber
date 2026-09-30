"""Dépendances FastAPI : utilisateur courant et contrôle du rôle administrateur."""
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, Response, status

from . import config, db
from .security import hash_token


@dataclass
class CurrentUser:
    nif: str
    email: str
    roles: list[str]
    token_hash: str

    @property
    def is_admin(self) -> bool:
        return config.ADMIN_ROLE in self.roles


def _read_token(request: Request) -> str | None:
    """Jeton lu dans le cookie (navigateur) ou l'en-tête Authorization (services tiers)."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.cookies.get(config.SESSION_COOKIE)


def current_user(request: Request) -> CurrentUser:
    token = _read_token(request)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Non authentifié")
    token_hash = hash_token(token)
    row = db.fetch_one(
        '''
        SELECT u."nif", u."email",
               COALESCE(array_agg(r."name" ORDER BY r."name") FILTER (WHERE r."name" IS NOT NULL), '{}') AS "roles"
        FROM "Session" s
        JOIN "User" u ON u."nif" = s."nif"
        LEFT JOIN "UserRole" ur ON ur."nif" = u."nif"
        LEFT JOIN "Role" r ON r."roleID" = ur."roleID"
        WHERE s."tokenHash" = %s AND s."expireAt" > now()
        GROUP BY u."nif", u."email"
        ''',
        (token_hash,),
    )
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expirée")
    return CurrentUser(row["nif"], row["email"], list(row["roles"]), token_hash)


def require_admin(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réservé aux administrateurs")
    return user


def _cookie_path(name: str) -> str:
    # Le cookie de session est envoyé à tout le site pour que les services protégés
    # (/impots, /intranet, /ficoba) le reçoivent ; le cookie MFA reste limité à l'API.
    return "/" if name == config.SESSION_COOKIE else "/api"


def set_cookie(response: Response, name: str, value: str, minutes: int):
    response.set_cookie(
        name, value,
        max_age=minutes * 60,
        httponly=True,            # inaccessible au JavaScript -> limite l'impact d'un XSS
        secure=config.COOKIE_SECURE,
        samesite="strict",        # jamais envoyé depuis un autre site -> protège du CSRF
        path=_cookie_path(name),
    )


def clear_cookie(response: Response, name: str):
    response.delete_cookie(name, path=_cookie_path(name), secure=config.COOKIE_SECURE, httponly=True, samesite="strict")
