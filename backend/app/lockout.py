"""Verrouillage des comptes.

Le compteur d'échecs est commun aux erreurs de mot de passe et de code TOTP,
à la connexion comme dans l'espace utilisateur : au 5e échec, le compte est
verrouillé pendant LOCK_MINUTES.
"""
from fastapi import HTTPException, Request, status

from . import config, db, events
from .security import verify_password

LOCKED = f"Compte verrouillé après {config.MAX_LOGIN_ATTEMPTS} échecs. Réessayez dans {config.LOCK_MINUTES} minutes."


def get_user(nif: str):
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


def clear_expired_lock(user):
    """Verrouillage expiré : le compteur repart de zéro."""
    if user["lockDate"] is not None and not user["locked"]:
        db.execute('UPDATE "User" SET "nbTry" = 0, "lockDate" = NULL WHERE "nif" = %s', (user["nif"],))
        user["nbTry"] = 0


def register_failure(request: Request, nif: str) -> bool:
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


def check_password(request: Request, nif: str, password: str, event_type: str):
    """Revérifie le mot de passe d'un utilisateur connecté avant une action sensible.

    Les erreurs comptent dans le verrouillage : un jeton de session volé ne permet pas
    de deviner le mot de passe. Au verrouillage, toutes les sessions sont fermées.
    """
    user = get_user(nif)
    if user["locked"]:
        raise HTTPException(status.HTTP_423_LOCKED, LOCKED)
    clear_expired_lock(user)
    if not verify_password(user["passwordHash"], password):
        events.log(request, event_type, False, nif, "mot de passe incorrect")
        if register_failure(request, nif):
            db.execute('DELETE FROM "Session" WHERE "nif" = %s', (nif,))
            raise HTTPException(status.HTTP_423_LOCKED, LOCKED)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Mot de passe incorrect")
