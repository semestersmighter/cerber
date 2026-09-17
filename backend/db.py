import os

import psycopg
from psycopg.rows import dict_row


# Défini dans docker-compose.yml ; la valeur par défaut sert en local hors Docker
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://cerber_admin:cerber_secure_pwd@localhost:5432/cerber_db")


def get_connection():
    # Connexion ouverte à la demande : l'API démarre même si la BDD n'est pas encore prête
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def get_user_by_nif(nif: str):
    # Requête paramétrée -> protège contre l'injection SQL
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT "nif", "passwordHash", "roleID", "nbTry", "lockDate" FROM "User" WHERE "nif" = %s',
                (nif,),
            )
            return cur.fetchone()

def get_role_by_token(token: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''SELECT u."roleID"
                   FROM "Session" s
                   JOIN "User" u ON u."nif" = s."nif"
                   WHERE s."sessionToken" = %s AND s."expireAt" > CURRENT_TIMESTAMP''',
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
                   VALUES (%s, %s, CURRENT_TIMESTAMP + (%s || ' minutes')::INTERVAL)''',
                (token, nif, expire_minutes),
            )
        conn.commit()