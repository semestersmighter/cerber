"""Configuration lue depuis les variables d'environnement (voir .env.example)."""
import os


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://cerber_admin:change_me@localhost:5432/cerber_db"
)

# Durées
SESSION_MINUTES = _int("SESSION_MINUTES", 60)
MFA_CHALLENGE_MINUTES = _int("MFA_CHALLENGE_MINUTES", 5)
LOCK_MINUTES = _int("LOCK_MINUTES", 15)
MAX_LOGIN_ATTEMPTS = _int("MAX_LOGIN_ATTEMPTS", 5)

# Cookies : Secure doit rester à true derrière HTTPS
COOKIE_SECURE = _bool("COOKIE_SECURE", True)
SESSION_COOKIE = "cerber_session"
MFA_COOKIE = "cerber_mfa"

# Noms d'hôte acceptés (en-tête Host transmis par nginx), séparés par des virgules.
# "*" accepte tout ; "*.exemple.fr" accepte les sous-domaines.
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "*").split(",") if h.strip()] or ["*"]

TOTP_ISSUER = os.getenv("TOTP_ISSUER", "CERBER")

ADMIN_ROLE = "Administrateur"
