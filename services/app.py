"""Service protégé par CERBER (maquette).

Le même code tourne dans 3 conteneurs ; SERVICE_SLUG choisit le service simulé.
À chaque requête, le service ne fait confiance à personne : il transmet le jeton
de session de l'utilisateur à CERBER (GET /api/access/{slug}) et n'affiche la page
que si CERBER répond 200.
"""
import html
import json
import os
import urllib.error
import urllib.request

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

SLUG = os.environ["SERVICE_SLUG"]
CERBER_API = os.getenv("CERBER_API", "http://backend:8000")
SESSION_COOKIE = "cerber_session"
# Même liste que le backend : Host transmis par nginx
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "*").split(",") if h.strip()] or ["*"]

# Contenu fictif de chaque service
CONTENT = {
    "impots": {
        "title": "Espace particulier",
        "intro": "Service en ligne des impôts des particuliers.",
        "columns": ("Document", "État"),
        "rows": [
            ("Déclaration de revenus 2025", "Déposée le 22/05/2026"),
            ("Avis d'impôt 2025", "Disponible"),
        ],
    },
    "intranet": {
        "title": "Intranet DGFIP",
        "intro": "Espace interne réservé aux personnels.",
        "columns": ("Date", "Actualité"),
        "rows": [
            ("24/09/2026", "Nouvelle procédure de connexion via CERBER"),
            ("18/09/2026", "Campagne de sensibilisation au hameçonnage"),
            ("02/09/2026", "Mise à jour du guide des procédures de contrôle"),
        ],
    },
    "ficoba": {
        "title": "FICOBA",
        "intro": "Fichier national des comptes bancaires et assimilés.",
        "columns": ("Titulaire (NIF)", "Établissement", "Type"),
        "rows": [
            ("3456789012345", "Banque Exemple", "Compte courant"),
            ("3456789012345", "Caisse Fictive", "Livret A"),
            ("4567890123456", "Banque Exemple", "Compte courant"),
        ],
    },
}[SLUG]

app = FastAPI(title=CONTENT["title"], docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)


def call_cerber(path: str, token: str, client_ip: str | None, host: str) -> tuple[int, dict]:
    """Appel à l'API CERBER avec le jeton de session de l'utilisateur."""
    req = urllib.request.Request(
        f"{CERBER_API}{path}",
        # Host public transmis tel quel : le backend applique le même ALLOWED_HOSTS
        headers={"Authorization": f"Bearer {token}", "X-Real-IP": client_ip or "", "Host": host},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as err:
        return err.code, {}
    except (urllib.error.URLError, TimeoutError):
        return 503, {}


def tax_rate_row(token: str, client_ip: str | None, host: str) -> tuple[str, str] | None:
    """Ligne « Prélèvement à la source » avec le taux fixé par les agents (contribuables uniquement)."""
    status, me = call_cerber("/api/me", token, client_ip, host)
    rate = me.get("tax_rate") if status == 200 else None
    if rate is None:
        return None
    return ("Prélèvement à la source", f"Taux personnalisé : {rate:.1f} %".replace(".", ","))


def page(title: str, body: str, status: int = 200) -> HTMLResponse:
    return HTMLResponse(
        f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="icon" href="/favicon.svg">
  <link rel="stylesheet" href="/css/style.css">
</head>
<body>
  <header><nav>
    <a class="brand" href="/services.html">CERBER</a>
    <a href="/services.html">Retour au portail</a>
  </nav></header>
  <main>
{body}
  </main>
</body>
</html>""",
        status_code=status,
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": SLUG}


@app.get(f"/{SLUG}")
@app.get(f"/{SLUG}/{{path:path}}")
def protected(request: Request, path: str = ""):
    token = request.cookies.get(SESSION_COOKIE)
    client = (request.headers.get("x-real-ip"), request.headers.get("host", ""))
    status, data = call_cerber(f"/api/access/{SLUG}", token, *client) if token else (401, {})

    if status == 401:
        # Pas connecté (ou session expirée) : passage par le portail puis retour ici
        return RedirectResponse(f"/?next=/{SLUG}/", status_code=303)

    if status == 403:
        return page(
            "Accès refusé",
            f"""    <h1>Accès refusé</h1>
    <p>Vos rôles ne vous permettent pas d'accéder à <strong>{html.escape(CONTENT["title"])}</strong>.</p>
    <p><a href="/services.html">Voir les services auxquels vous avez accès</a></p>""",
            403,
        )

    if status != 200:
        return page("Service indisponible",
                    "    <h1>Service indisponible</h1>\n    <p>CERBER ne répond pas. Réessayez dans un instant.</p>", 503)

    table = list(CONTENT["rows"])
    if SLUG == "impots" and (row := tax_rate_row(token, *client)):
        table.append(row)

    head = "".join(f"<th>{html.escape(c)}</th>" for c in CONTENT["columns"])
    rows = "".join(
        "<tr>" + "".join(f"<td>{html.escape(v)}</td>" for v in row) + "</tr>" for row in table
    )
    return page(
        CONTENT["title"],
        f"""    <h1>{html.escape(CONTENT["title"])}</h1>
    <p>{html.escape(CONTENT["intro"])}</p>
    <p class="muted">Connecté : NIF {html.escape(data["nif"])} · {html.escape(", ".join(data["roles"]))}
      · accès vérifié par CERBER</p>
    <div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>""",
    )
