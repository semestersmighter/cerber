"""Tests de bout en bout de l'API (nécessitent une base PostgreSQL de test).

    DATABASE_URL=postgresql://... pytest backend/tests

ATTENTION : la base est entièrement réinitialisée avec init.sql.
"""
from pathlib import Path

import psycopg
import pyotp
import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app

ADMIN = ("1234567890123", "Cerber-Admin-2026!")
AGENT = ("2345678901234", "Cerber-Agent-2026!")
CONTRIB = ("3456789012345", "Cerber-Contrib-2026!")
LOCKED = ("4567890123456", "Cerber-Locked-2026!")
NEW_PASSWORD = "Nouveau-Mot2Passe!"


@pytest.fixture(scope="module", autouse=True)
def fresh_db():
    reset_db()


def reset_db():
    sql = (Path(__file__).parents[1] / "init.sql").read_text()
    with psycopg.connect(config.DATABASE_URL, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        conn.execute(sql)


def client() -> TestClient:
    # https : les cookies sont marqués Secure
    return TestClient(app, base_url="https://testserver")


def fresh_code(nif: str) -> str:
    """Code TOTP courant. L'anti-rejeu refuse un pas déjà utilisé : les tests enchaînant
    plusieurs connexions dans la même fenêtre de 30 s, on remet ce compteur à zéro."""
    with psycopg.connect(config.DATABASE_URL) as conn:
        conn.execute('UPDATE "User" SET "totpLastStep" = 0 WHERE "nif" = %s', (nif,))
    return pyotp.TOTP(secrets_by_nif[nif]).now()


secrets_by_nif: dict[str, str] = {}


def login(c: TestClient, nif: str, password: str):
    r = c.post("/api/auth/login", json={"nif": nif, "password": password})
    assert r.status_code == 200, r.text
    if not r.json()["totp_enrolled"]:
        setup = c.get("/api/auth/totp/setup").json()
        assert setup["qr_svg"].startswith("<svg")
        secrets_by_nif[nif] = setup["secret"]
        code = pyotp.TOTP(setup["secret"]).now()
    else:
        code = fresh_code(nif)
    r = c.post("/api/auth/mfa", json={"code": code})
    assert r.status_code == 200, r.text
    return c


def test_login_and_first_enrollment():
    with client() as c:
        login(c, *ADMIN)
        me = c.get("/api/me").json()
        assert me["nif"] == ADMIN[0] and me["is_admin"] and me["totp_enabled"]


def test_mfa_required_before_session():
    with client() as c:
        c.post("/api/auth/login", json={"nif": ADMIN[0], "password": ADMIN[1]})
        assert c.get("/api/me").status_code == 401


def test_totp_replay_rejected():
    with client() as c:
        c.post("/api/auth/login", json={"nif": ADMIN[0], "password": ADMIN[1]})
        # le pas le plus récent a déjà été consommé par la connexion précédente
        r = c.post("/api/auth/mfa", json={"code": pyotp.TOTP(secrets_by_nif[ADMIN[0]]).now()})
        assert r.status_code == 401


def test_wrong_password_and_unknown_nif_same_message():
    with client() as c:
        a = c.post("/api/auth/login", json={"nif": CONTRIB[0], "password": "mauvais"})
        b = c.post("/api/auth/login", json={"nif": "9999999999999", "password": "mauvais"})
        assert a.status_code == b.status_code == 401
        assert a.json() == b.json()


def test_lock_after_five_failures():
    with client() as c:
        for _ in range(4):
            assert c.post("/api/auth/login", json={"nif": AGENT[0], "password": "x"}).status_code == 401
        assert c.post("/api/auth/login", json={"nif": AGENT[0], "password": "x"}).status_code == 423
        # même le bon mot de passe est refusé
        assert c.post("/api/auth/login", json={"nif": AGENT[0], "password": AGENT[1]}).status_code == 423


def test_seeded_locked_account():
    with client() as c:
        assert c.post("/api/auth/login", json={"nif": LOCKED[0], "password": LOCKED[1]}).status_code == 423


def test_admin_unlocks_account():
    with client() as c:
        login(c, *ADMIN)
        assert c.post(f"/api/admin/users/{AGENT[0]}/unlock").status_code == 200
    with client() as c:
        login(c, *AGENT)


def test_seeded_services_use_relative_urls():
    # Aucun lien vers localhost : les services suivent l'adresse utilisée pour ouvrir le portail
    with client() as c:
        login(c, *CONTRIB)
        assert [r["url"] for r in c.get("/api/me/resources").json()] == ["/impots/"]


def test_access_control_by_role():
    with client() as c:
        login(c, *CONTRIB)
        assert c.get("/api/access/impots").status_code == 200
        assert c.get("/api/access/ficoba").status_code == 403
        assert c.get("/api/access/inconnue").status_code == 404
        slugs = [r["slug"] for r in c.get("/api/me/resources").json()]
        assert slugs == ["impots"]
        assert c.get("/api/admin/users").status_code == 403


def test_bearer_token_for_services():
    with client() as c:
        login(c, *AGENT)
        token = c.cookies.get(config.SESSION_COOKIE)
    with client() as other:
        r = other.get("/api/access/ficoba", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200 and r.json()["nif"] == AGENT[0]


def test_refresh_rotates_token():
    with client() as c:
        login(c, *CONTRIB)
        old = c.cookies.get(config.SESSION_COOKIE)
        assert c.post("/api/auth/refresh").status_code == 200
        new = c.cookies.get(config.SESSION_COOKIE)
        assert new and new != old
        assert c.get("/api/me").status_code == 200
    with client() as other:
        assert other.get("/api/me", headers={"Authorization": f"Bearer {old}"}).status_code == 401


def test_profile_update_and_password_change():
    with client() as c:
        login(c, *CONTRIB)
        r = c.patch("/api/me", json={"email": "jean.martin@nouveau.fr", "address": "1 place de la Mairie, 69001 Lyon"})
        assert r.status_code == 200
        assert c.get("/api/me").json()["address"].startswith("1 place")
        # email déjà pris
        assert c.patch("/api/me", json={"email": "admin.cerber@dgfip.gouv.fr", "address": ""}).status_code == 409
        # politique ANSSI
        weak = c.post("/api/me/password", json={"current_password": CONTRIB[1], "new_password": "court"})
        assert weak.status_code == 422 and "15 caractères" in weak.json()["detail"]
        ok = c.post("/api/me/password", json={"current_password": CONTRIB[1], "new_password": NEW_PASSWORD})
        assert ok.status_code == 200
    with client() as c:
        login(c, CONTRIB[0], NEW_PASSWORD)


def test_forgot_password_with_totp():
    nif = CONTRIB[0]
    with client() as c:
        bad = c.post("/api/auth/password/forgot", json={"nif": nif, "code": "000000", "new_password": CONTRIB[1]})
        assert bad.status_code == 401
        ok = c.post("/api/auth/password/forgot",
                    json={"nif": nif, "code": fresh_code(nif), "new_password": CONTRIB[1]})
        assert ok.status_code == 200, ok.text
    with client() as c:
        r = c.post("/api/auth/login", json={"nif": nif, "password": CONTRIB[1]})
        assert r.status_code == 200


def test_change_totp_app():
    with client() as c:
        login(c, *AGENT)
        assert c.post("/api/me/totp/renew", json={"password": "faux"}).status_code == 401
        setup = c.post("/api/me/totp/renew", json={"password": AGENT[1]}).json()
        assert c.post("/api/me/totp/confirm", json={"code": pyotp.TOTP(setup["secret"]).now()}).status_code == 200
        secrets_by_nif[AGENT[0]] = setup["secret"]
    with client() as c:
        login(c, *AGENT)


def test_admin_users_resources_and_events():
    with client() as c:
        login(c, *ADMIN)
        roles = {r["name"]: r["id"] for r in c.get("/api/admin/roles").json()}

        new_user = {"nif": "5678901234567", "email": "nouvel.agent@dgfip.gouv.fr", "address": "",
                    "password": "Motdepasse-Solide1!", "role_ids": [roles["Agent DGFIP"]]}
        assert c.post("/api/admin/users", json={**new_user, "password": "faible"}).status_code == 422
        assert c.post("/api/admin/users", json=new_user).status_code == 201
        assert c.post("/api/admin/users", json=new_user).status_code == 409
        assert c.post("/api/admin/users", json={**new_user, "nif": "123"}).json()["detail"].startswith("Champ invalide")

        res = {"slug": "cadastre", "name": "Cadastre", "url": "/cadastre/", "role_ids": [roles["Agent DGFIP"]]}
        assert c.post("/api/admin/resources", json={**res, "url": "javascript:alert(1)"}).status_code == 422
        assert c.post("/api/admin/resources", json={**res, "url": "//evil.example/"}).status_code == 422
        rid = c.post("/api/admin/resources", json=res).json()["id"]

    with client() as u:
        login(u, new_user["nif"], new_user["password"])
        assert u.get("/api/access/cadastre").status_code == 200

    with client() as c:
        login(c, *ADMIN)
        assert c.put(f"/api/admin/resources/{rid}/roles", json={"role_ids": [roles["Administrateur"]]}).status_code == 200
        assert c.get("/api/access/cadastre").status_code == 200
        assert c.delete(f"/api/admin/resources/{rid}").status_code == 200
        assert c.delete(f"/api/admin/users/{new_user['nif']}").status_code == 200
        assert c.delete(f"/api/admin/users/{ADMIN[0]}").status_code == 400

        data = c.get("/api/admin/events").json()
        types = {e["type"] for e in data["events"]}
        assert {"LOGIN", "MFA", "ACCOUNT_LOCKED", "TOTP_ENROLLED", "TOKEN_RENEWED",
                "PASSWORD_RESET", "ACCESS_CHECK", "ADMIN"} <= types
        failures = c.get("/api/admin/events", params={"type": "LOGIN", "success": "false"}).json()["events"]
        assert failures and all(not e["success"] for e in failures)


def test_agent_updates_tax_rate():
    with client() as c:
        login(c, *CONTRIB)
        assert c.get("/api/me").json()["tax_rate"] == 7.5
        # un contribuable ne modifie pas son taux
        assert c.put(f"/api/tax/taxpayers/{CONTRIB[0]}", json={"rate": 0}).status_code == 403

    with client() as c:
        login(c, *AGENT)
        taxpayers = {t["nif"]: t for t in c.get("/api/tax/taxpayers").json()}
        assert set(taxpayers) == {CONTRIB[0], LOCKED[0]}  # uniquement des contribuables
        assert c.get("/api/tax/taxpayers", params={"nif": "345"}).json()[0]["nif"] == CONTRIB[0]
        assert c.get("/api/tax/taxpayers", params={"nif": "3%"}).status_code == 422

        assert c.put(f"/api/tax/taxpayers/{CONTRIB[0]}", json={"rate": 61}).status_code == 422
        assert c.put(f"/api/tax/taxpayers/{CONTRIB[0]}", json={"rate": 7.55}).status_code == 422
        assert c.put(f"/api/tax/taxpayers/{ADMIN[0]}", json={"rate": 10}).status_code == 404
        assert c.put(f"/api/tax/taxpayers/{AGENT[0]}", json={"rate": 10}).status_code == 403
        r = c.put(f"/api/tax/taxpayers/{CONTRIB[0]}", json={"rate": 12.4})
        assert r.status_code == 200 and r.json()["rate"] == 12.4

    with client() as c:
        login(c, *CONTRIB)
        assert c.get("/api/me").json()["tax_rate"] == 12.4

    with client() as c:
        login(c, *ADMIN)
        # l'administrateur ne modifie pas les taux...
        assert c.get("/api/tax/taxpayers").status_code == 403
        events = c.get("/api/admin/events", params={"type": "TAX_RATE"}).json()["events"]
        assert events[0]["nif"] == AGENT[0] and "7.5 % -> 12.4 %" in events[0]["detail"]
        # ...mais il choisit les rôles qui en ont le droit
        roles = {r["name"]: r["id"] for r in c.get("/api/admin/roles").json()}
        taux = next(r for r in c.get("/api/admin/resources").json() if r["slug"] == "taux")
        c.put(f"/api/admin/resources/{taux['id']}/roles", json={"role_ids": [roles["Administrateur"]]})
        assert c.get("/api/tax/taxpayers").status_code == 200

    with client() as c:
        login(c, *AGENT)
        assert c.put(f"/api/tax/taxpayers/{CONTRIB[0]}", json={"rate": 5}).status_code == 403


def test_logout():
    with client() as c:
        login(c, *ADMIN)
        assert c.post("/api/auth/logout").status_code == 200
        assert c.get("/api/me").status_code == 401


# Matrice des droits attendue pour les 3 services simulés (conteneurs svc-*) et la page des taux
ACCESS_MATRIX = {
    #            impots intranet ficoba taux
    ADMIN:   (False, True,  False, False),
    AGENT:   (True,  True,  True,  True),
    CONTRIB: (True,  False, False, False),
}


@pytest.mark.parametrize("user", list(ACCESS_MATRIX), ids=["admin", "agent", "contribuable"])
def test_access_matrix(user):
    reset_db()  # données de départ (le test des ressources modifie les droits)
    secrets_by_nif.clear()
    with client() as c:
        login(c, *user)
        for slug, expected in zip(("impots", "intranet", "ficoba", "taux"), ACCESS_MATRIX[user]):
            status = c.get(f"/api/access/{slug}").status_code
            assert status == (200 if expected else 403), f"{user[0]} -> {slug}: {status}"
