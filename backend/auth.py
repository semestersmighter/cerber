import psycopg
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

import db

router = APIRouter(prefix="/api/auth", tags=["auth"])
password_hasher = PasswordHasher()


class LoginRequest(BaseModel):
    nif: str
    password: str


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


@router.post("/login")
def login(credentials: LoginRequest):
    try:
        user = db.get_user_by_nif(credentials.nif)
    except psycopg.OperationalError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Base de données indisponible")

    # Même message que l'utilisateur existe ou non, pour ne pas révéler les comptes valides
    if user is None or not verify_password(user["passwordHash"], credentials.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiants invalides")

    return {"message": "Connexion réussie", "nif": user["nif"], "roleID": user["roleID"]}
