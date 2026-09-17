import psycopg
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

import db

router = APIRouter(prefix="/api/auth", tags=["auth"])
password_hasher = PasswordHasher()

LOCK_DURATION_MINUTES = 15


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
        user = db.get_user_by_nif(credentials.nif, LOCK_DURATION_MINUTES)
        if user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiants invalides")

        # Compte verrouillé : on ne vérifie même pas le mot de passe
        if user["isLocked"]:
            raise HTTPException(
                status.HTTP_423_LOCKED,
                f"Compte verrouillé après {db.MAX_LOGIN_ATTEMPTS} échecs, réessayez plus tard",
            )

        # Verrouillage expiré : on repart de zéro
        if user["lockDate"] is not None:
            db.reset_failed_attempts(user["nif"])
            user["nbTry"] = 0

        if not verify_password(user["passwordHash"], credentials.password):
            db.register_failed_attempt(user["nif"])
            # Même message que pour un compte inexistant, pour ne pas révéler les comptes valides
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiants invalides")

        if user["nbTry"] > 0:
            db.reset_failed_attempts(user["nif"])
    except psycopg.OperationalError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Base de données indisponible")

    return {"message": "Connexion réussie", "nif": user["nif"], "roleID": user["roleID"]}
