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
                SELECT "nif", "passwordHash", "roleID", "nbTry", "lockDate",
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
