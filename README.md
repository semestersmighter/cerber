# CERBER

## Objectifs

Après avoir subi une cyberattaque sur ses systèmes d'information, la DGFIP a décidé de solliciter notre entreprise afin de développer un nouveau portail d'authentification qui sera utilisé comme SSO sur l'ensemble de ses services. 
CERBER est un système d'authentification qui a pour but de sécuriser l'accès a plusieurs services numériques.


## Spécifications fonctionnelles

Ce portail doit comprendre les fonctionnalités et prérequis suivants :
* Mise en place d'une authentification multi facteur « MFA » : 
* Système de connexion par numéro fiscal et mot de passe. 
* Code aléatoire envoyé par mail à l’utilisateur 
* Vérification de l’accès à une ressource selon le rôle de l’utilisateur. 
* Après 5 tentatives de connexion échouées, le compte est verrouillé. 
* L'utilisateur peut réinitialiser son mot de passe. 
* L'utilisateur peut mettre à jour ses informations personnelles (email, adresse postale). 
* L’utilisateur peut changer un facteur d’authentification (code par mail, TOTP) 
* L’administrateur peut accéder à la traçabilité sur les événements d'authentification : succès, échec, demande de réinitialisation, renouvellement de jetons, MFA. 
* L’administrateur peut créer un nouveau compte. 
* L’administrateur peut supprimer un compte. 
* L’administrateur peut ajouter une nouvelle ressource. 
* L’administrateur peut configurer l’accès à une ressource suivant le rôle de l’utilisateur. 
* L’agent peut modifier le taux d’imposition (prélèvement à la source) d’un contribuable. 

## Spécifications techniques
* Base de données pour la gestion des utilisateurs -> SQL. 
* Accès au service via une interface web en HTTPS. 
* Création d’un système d’authentification basé sur un jeton. 
* Langages utilisés en Frontend : HTML, CSS, JS 
* Langages utilisés en Backend : FastAPI (Python) 

## Architecture

```
                                   ┌──/api──────> backend (FastAPI) ──> PostgreSQL
navigateur ──HTTPS──> nginx ───────┤                 ▲
                   (frontend/)     ├──/impots───> svc-impots   ─┐
                                   ├──/intranet─> svc-intranet ─┼─ GET /api/access/{slug}
                                   └──/ficoba───> svc-ficoba   ─┘   (Bearer <jeton>)
```

* **Front** (`frontend/public`) : pages HTML statiques, une feuille de style, un petit fichier JS
  commun (`js/app.js`) et un script par page pour les appels à l'API. Aucun framework, aucune étape de build.
* **nginx** sert les pages en HTTPS et transmet `/api` au backend : front et API ont la même origine,
  donc pas de CORS. Il ajoute les en-têtes de sécurité (CSP stricte, HSTS…).
* **Backend** (`backend/app`) : FastAPI + psycopg (pool de connexions), requêtes SQL paramétrées.
* **Jeton de session** : aléatoire (256 bits), stocké **haché** (SHA-256) en base, envoyé dans un cookie
  `HttpOnly; Secure; SameSite=Strict` valable sur tout le site, pour que les services le reçoivent. Les services tiers peuvent aussi l'envoyer dans l'en-tête
  `Authorization: Bearer`.

### Services protégés (simulation de l'intranet)

Trois conteneurs (`services/`, même image, variable `SERVICE_SLUG`) simulent les services de la DGFIP.
Ils ne publient aucun port et ne sont joignables qu'à travers nginx.

À **chaque requête**, le service transmet le jeton de session de l'utilisateur à CERBER
(`GET /api/access/{slug}`) et affiche la page seulement si CERBER répond 200 :

* pas de session ou session expirée : redirection vers la connexion, puis retour automatique au service ;
* rôle non autorisé : page « Accès refusé » (403).

Un changement de droits dans la page Administration s'applique donc immédiatement,
sans reconnexion.

Les adresses des services sont des **chemins relatifs** (`/intranet/`) : les liens et redirections
suivent le nom d'hôte utilisé pour ouvrir le portail (localhost, IP du serveur, nom de domaine…).
Une ressource externe peut aussi être déclarée avec une URL complète `https://…` (le HTTP en clair est refusé).

| Service | URL | Administrateur | Agent DGFIP | Contribuable |
|---|---|:-:|:-:|:-:|
| Espace particulier | `/impots/` | ✗ | ✓ | ✓ |
| Intranet DGFIP | `/intranet/` | ✓ | ✓ | ✗ |
| FICOBA | `/ficoba/` | ✗ | ✓ | ✗ |
| Taux d'imposition (page du portail) | `/taux.html` | ✗ | ✓ | ✗ |

Pour ajouter un service : ajouter un conteneur `svc-xxx` dans `docker-compose.yml`, une `location /xxx`
dans `frontend/nginx.conf.template`, son contenu dans `services/app.py`, puis déclarer la ressource `xxx`
dans la page Administration.

### Parcours de connexion

1. NIF + mot de passe (Argon2id). En cas de succès, un cookie temporaire `cerber_mfa` (5 min) est émis.
2. Première connexion : un QR code TOTP s'affiche et l'utilisateur le scanne (Google Authenticator, FreeOTP…).
3. Code TOTP à 6 chiffres, avec anti-rejeu : un même code ne sert qu'une fois. Le cookie de session `cerber_session` (60 min) est alors émis.

Le compteur d'échecs cumule les erreurs de mot de passe **et** de code TOTP, y compris le mot de passe
redemandé dans « Mon compte » (changement de mot de passe ou d'application TOTP) : un jeton de session
volé ne permet donc pas de deviner le mot de passe. Au 5e échec, le compte est verrouillé pendant 15 min
(ou jusqu'au déverrouillage par un administrateur) et ses sessions ouvertes sont fermées.

### Taux d'imposition

Les agents modifient le taux de prélèvement à la source des contribuables (0 à 60 %, une décimale)
depuis la page `/taux.html`, listée dans « Mes services ». Les droits passent par la ressource `taux` :
l'administrateur choisit dans la page Administration quels rôles y ont accès (Agent DGFIP par défaut).
Un agent ne peut modifier ni son propre taux ni celui d'un compte qui n'est pas contribuable.
Chaque modification est tracée (`TAX_RATE`, avec l'ancien et le nouveau taux) et le contribuable voit
son taux dans l'Espace particulier (`/impots/`).

## Lancement

```bash
cp .env.example .env        # puis changer POSTGRES_PASSWORD et DATABASE_URL
docker compose up -d --build
```

* Application : https://localhost:8443 (certificat auto-signé, à accepter dans le navigateur ;
  pour un autre nom, l'ajouter à `ALLOWED_HOSTS`)
* Documentation de l'API (Swagger) : https://localhost:8443/api/docs

> `init.sql` n'est exécuté que si la base est vide. Après une modification du schéma :
> `docker compose down -v && docker compose up -d --build`.

### Nom d'hôte et en-têtes (`.env`)

| Variable | Valeurs | Rôle |
|---|---|---|
| `HOST_HEADER` | `host` (défaut) · `x-forwarded-host` | En-tête qui donne le nom d'hôte public. `x-forwarded-host` sert quand CERBER est derrière un autre reverse proxy (Traefik, load balancer…). |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` · `portail.dgfip.fr,*.dgfip.fr` · `*` | Noms d'hôte acceptés. Tout autre hôte est refusé : `421` par nginx, `400` par le backend et les services (défense en profondeur). |
| `HTTPS_PORT` | `8443` · `443` | Port HTTPS publié, utilisé aussi dans la redirection HTTP → HTTPS (omis s'il vaut 443). |
| `HTTP_PORT` | `8080` · `80` | Port HTTP publié (redirige vers HTTPS). |

nginx transmet ensuite l'hôte validé au backend et aux services (`Host` et `X-Forwarded-Host`).
Aucune adresse n'est codée en dur : les liens et redirections suivent cet hôte.

> Avec `HOST_HEADER=x-forwarded-host`, n'exposez nginx **qu'au proxy de confiance** :
> un client qui l'atteint directement pourrait choisir lui-même la valeur de l'en-tête
> (elle reste toutefois limitée à `ALLOWED_HOSTS`).

La configuration nginx est générée au démarrage du conteneur à partir de
`frontend/nginx.conf.template` par `frontend/docker-entrypoint.d/30-cerber-config.sh`.
Une valeur invalide empêche le démarrage, avec un message explicite dans `docker compose logs frontend`.

### Comptes de démonstration

| NIF | Mot de passe | Rôle |
|---|---|---|
| 1234567890123 | `Cerber-Admin-2026!` | Administrateur |
| 2345678901234 | `Cerber-Agent-2026!` | Agent DGFIP |
| 3456789012345 | `Cerber-Contrib-2026!` | Contribuable |
| 4567890123456 | `Cerber-Locked-2026!` | Contribuable (compte verrouillé) |

## Pages

| Page | Rôle |
|---|---|
| `/` | Connexion (NIF + mot de passe) |
| `/mfa.html` | Code TOTP, et QR code à la première connexion |
| `/forgot.html` | Mot de passe oublié (NIF + code TOTP + nouveau mot de passe) |
| `/services.html` | Services accessibles selon les rôles |
| `/account.html` | Email, adresse, mot de passe, changement d'application TOTP |
| `/admin.html` | Comptes, ressources et droits par rôle, journal d'authentification |
| `/taux.html` | Taux d'imposition des contribuables (agents) |

## API

| Méthode | Route | Description |
|---|---|---|
| POST | `/api/auth/login` | `{nif, password}` → `{totp_enrolled}` + cookie `cerber_mfa` |
| GET | `/api/auth/totp/setup` | 1re connexion : `{secret, qr_svg}` |
| POST | `/api/auth/mfa` | `{code}` → cookie `cerber_session` |
| POST | `/api/auth/refresh` | Renouvelle le jeton (l'ancien est invalidé) |
| POST | `/api/auth/logout` | Ferme la session |
| POST | `/api/auth/password/forgot` | `{nif, code, new_password}` |
| GET / PATCH | `/api/me` | Profil (avec `tax_rate` pour un contribuable) / `{email, address}` |
| POST | `/api/me/password` | `{current_password, new_password}` |
| POST | `/api/me/totp/renew` puis `/api/me/totp/confirm` | Changement d'application TOTP |
| GET | `/api/me/resources` | Ressources accessibles |
| GET | `/api/access/{slug}` | Contrôle d'accès : 200 si autorisé, 403 sinon |
| GET / POST | `/api/admin/users` | Liste / création de compte |
| DELETE | `/api/admin/users/{nif}` | Suppression |
| POST | `/api/admin/users/{nif}/unlock` · `/reset-totp` | Déverrouillage / réinitialisation TOTP |
| GET / POST | `/api/admin/resources` | Liste / ajout de ressource |
| PUT | `/api/admin/resources/{id}/roles` | `{role_ids}` : rôles autorisés |
| DELETE | `/api/admin/resources/{id}` | Suppression |
| GET | `/api/admin/roles` | Rôles |
| GET | `/api/admin/events?type=&nif=&success=` | Journal (LOGIN, MFA, ACCOUNT_LOCKED, TOKEN_RENEWED, PASSWORD_RESET, TAX_RATE…) |
| GET | `/api/tax/taxpayers?nif=` | Contribuables et leur taux (rôles autorisés sur `taux`) |
| PUT | `/api/tax/taxpayers/{nif}` | `{rate}` : nouveau taux |
| GET | `/api/health` | État de l'API et de la base |

### Exemples de calls API

```bash
B=https://localhost:8443/api
# 1. mot de passe
curl -k -c jar -H 'Content-Type: application/json' \
     -d '{"nif":"1234567890123","password":"Cerber-Admin-2026!"}' $B/auth/login
# 2. code TOTP
curl -k -b jar -c jar -H 'Content-Type: application/json' -d '{"code":"123456"}' $B/auth/mfa
# 3. appels authentifiés
curl -k -b jar $B/me
curl -k -b jar "$B/admin/events?type=LOGIN&success=false"

# Un service protégé vérifie l'accès d'un utilisateur avec son jeton :
curl -k -H "Authorization: Bearer <jeton>" $B/access/impots
```

## Tests

```bash
cd backend
pip install -r requirements.txt pytest httpx
# ATTENTION : la base ciblée est entièrement réinitialisée
DATABASE_URL=postgresql://cerber_admin:change_me@localhost:5432/cerber_test pytest tests
```

## Hors périmètre 

* Gestion des utilisateurs (LDAP chez le client)
* Inscription libre (les comptes sont créés par l'administrateur)
* Envoi de mails (le second facteur est le TOTP)

## Annexe 
* Protection contre les attaques courantes (injection SQL, XSS). 
* Politique de mot de passe : 15 caractères minimum (majuscules, minuscules, caractères spéciaux) selon l'ANSSI (ANSSI-PG-078). 
* S'adapte en temps réel en fonction du nombre d'utilisateurs connectés. 

 
