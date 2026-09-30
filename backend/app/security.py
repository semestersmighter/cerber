"""Primitives de sécurité : mots de passe, jetons, TOTP."""
import hashlib
import hmac
import re
import secrets
import time

import pyotp
import segno
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from . import config

_hasher = PasswordHasher()
# Empreinte factice : on vérifie un mot de passe même pour un NIF inconnu,
# pour que le temps de réponse ne révèle pas l'existence d'un compte.
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing")


# ---------- Mots de passe ----------

PASSWORD_MIN_LENGTH = 15
PASSWORD_RULES = (
    (lambda p: len(p) >= PASSWORD_MIN_LENGTH, f"au moins {PASSWORD_MIN_LENGTH} caractères"),
    (lambda p: re.search(r"[a-z]", p), "une minuscule"),
    (lambda p: re.search(r"[A-Z]", p), "une majuscule"),
    (lambda p: re.search(r"[0-9]", p), "un chiffre"),
    (lambda p: re.search(r"[^A-Za-z0-9]", p), "un caractère spécial"),
)


def password_problems(password: str) -> list[str]:
    """Règles ANSSI non respectées (liste vide si le mot de passe est conforme)."""
    return [label for rule, label in PASSWORD_RULES if not rule(password)]


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


# ---------- Jetons ----------

def new_token() -> tuple[str, str]:
    """Renvoie (jeton envoyé au client, empreinte stockée en base)."""
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ---------- TOTP (RFC 6238, 30 s, 6 chiffres) ----------

TOTP_PERIOD = 30


def new_totp_secret() -> str:
    return pyotp.random_base32()


def totp_uri(secret: str, account: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=account, issuer_name=config.TOTP_ISSUER)


def totp_qr_svg(uri: str) -> str:
    """QR code en SVG (généré côté serveur, aucune librairie JS nécessaire)."""
    return segno.make(uri, error="m").svg_inline(scale=5, dark="#111", light="#fff")


def verify_totp(secret: str, code: str, last_step: int) -> int | None:
    """Vérifie un code en tolérant ±1 période de décalage d'horloge.

    Renvoie le pas temporel accepté, ou None. Un pas déjà utilisé est refusé
    (protection contre le rejeu d'un code intercepté).
    """
    if not re.fullmatch(r"\d{6}", code or ""):
        return None
    totp = pyotp.TOTP(secret)
    current = int(time.time()) // TOTP_PERIOD
    for step in (current - 1, current, current + 1):
        if step > last_step and hmac.compare_digest(totp.at(step * TOTP_PERIOD), code):
            return step
    return None
