"""Accès PostgreSQL via un pool de connexions.

Toutes les requêtes sont paramétrées (%s) : aucune concaténation de chaînes,
ce qui protège contre l'injection SQL.
"""
from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from . import config

pool: ConnectionPool | None = None


def open_pool():
    """Ouvert au démarrage de l'API sans attendre la base : l'API démarre même si
    PostgreSQL n'est pas encore prêt. Le pool s'agrandit avec la charge (1 à 20 connexions)."""
    global pool
    pool = ConnectionPool(
        config.DATABASE_URL,
        min_size=1,
        max_size=20,
        timeout=5,  # délai max pour obtenir une connexion
        kwargs={"row_factory": dict_row},
        open=False,
    )
    pool.open(wait=False)


def close_pool():
    if pool is not None:
        pool.close()


@contextmanager
def transaction():
    """Connexion dont le travail est validé en fin de bloc (ou annulé en cas d'erreur)."""
    with pool.connection() as conn:
        with conn.transaction():
            yield conn


def fetch_one(sql: str, params: tuple = ()):
    with pool.connection() as conn:
        return conn.execute(sql, params).fetchone()


def fetch_all(sql: str, params: tuple = ()):
    with pool.connection() as conn:
        return conn.execute(sql, params).fetchall()


def execute(sql: str, params: tuple = ()):
    """Exécute une écriture et renvoie la première ligne si la requête a un RETURNING."""
    with pool.connection() as conn:
        cur = conn.execute(sql, params)
        return cur.fetchone() if cur.description else None
