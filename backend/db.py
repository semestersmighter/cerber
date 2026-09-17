import os

import psycopg
from psycopg.rows import dict_row


# Défini dans docker-compose.yml ; la valeur par défaut sert en local hors Docker
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://cerber_admin:cerber_secure_pwd@localhost:5432/cerber_db")

MAX_LOGIN_ATTEMPTS = 5


def get_connection():
    # Connexion ouverte à la demande : l'API démarre même si la BDD n'est pas encore prête
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def get_user_by_nif(nif: str, lock_minutes: int):
    # Requête paramétrée -> protège contre l'injection SQL
    # "isLocked" est calculé côté PostgreSQL pour éviter les soucis de fuseau horaire
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT "nif", "passwordHash", "nbTry", "lockDate",
                       ("lockDate" IS NOT NULL
                        AND "lockDate" > LOCALTIMESTAMP - make_interval(mins => %s)) AS "isLocked"
                FROM "User" WHERE "nif" = %s
                ''',
                (lock_minutes, nif),
            )
            return cur.fetchone()


def register_failed_attempt(nif: str):
    # Incrément atomique ; le compte est verrouillé dès que le seuil est atteint
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                UPDATE "User"
                SET "nbTry" = "nbTry" + 1,
                    "lockDate" = CASE WHEN "nbTry" + 1 >= %s THEN LOCALTIMESTAMP ELSE "lockDate" END
                WHERE "nif" = %s
                RETURNING "nbTry"
                ''',
                (MAX_LOGIN_ATTEMPTS, nif),
            )
            return cur.fetchone()["nbTry"]


def reset_failed_attempts(nif: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('UPDATE "User" SET "nbTry" = 0, "lockDate" = NULL WHERE "nif" = %s', (nif,))


def get_role_by_token(token: str):
    # Un utilisateur peut avoir plusieurs rôles (table "UserRole")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT s."nif", COALESCE(array_agg(ur."roleID") FILTER (WHERE ur."roleID" IS NOT NULL), '{}') AS "roleIDs"
                   FROM "Session" s
                   LEFT JOIN "UserRole" ur ON ur."nif" = s."nif"
                   WHERE s."sessionToken" = %s AND s."expireAt" > CURRENT_TIMESTAMP
                   GROUP BY s."nif"''',
                (token,),
            )
            return cur.fetchone()


def create_session(nif: str, token: str, expire_minutes: int = 60):
    with get_connection() as conn:
        with conn.cursor() as cur:
            # On supprime l'ancienne session de l'utilisateur (car "nif" est UNIQUE dans Session)
            cur.execute('DELETE FROM "Session" WHERE "nif" = %s', (nif,))
            cur.execute(
                '''INSERT INTO "Session" ("sessionToken", "nif", "expireAt")
                   VALUES (%s, %s, CURRENT_TIMESTAMP + make_interval(mins => %s))''',
                (token, nif, expire_minutes),
            )
