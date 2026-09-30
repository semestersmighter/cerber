-- ==========================================
-- CERBER - schéma de la base
-- Exécuté automatiquement au premier démarrage du conteneur PostgreSQL
-- ==========================================

CREATE TABLE "Role" (
    "roleID" SERIAL PRIMARY KEY,
    "name"   VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE "User" (
    "nif"               VARCHAR(13) PRIMARY KEY,
    "passwordHash"      VARCHAR(255) NOT NULL,
    "email"             VARCHAR(255) NOT NULL UNIQUE,
    "address"           VARCHAR(500) NOT NULL DEFAULT '',
    "nbTry"             INTEGER NOT NULL DEFAULT 0,
    "lockDate"          TIMESTAMPTZ NULL,
    -- TOTP : secret actif, secret en attente de confirmation, dernier pas utilisé (anti-rejeu)
    "totpSecret"        VARCHAR(64) NULL,
    "totpPendingSecret" VARCHAR(64) NULL,
    "totpLastStep"      BIGINT NOT NULL DEFAULT 0,
    "createdAt"         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Un utilisateur peut avoir plusieurs rôles
CREATE TABLE "UserRole" (
    "nif"    VARCHAR(13) NOT NULL REFERENCES "User"("nif") ON DELETE CASCADE,
    "roleID" INTEGER     NOT NULL REFERENCES "Role"("roleID") ON DELETE CASCADE,
    PRIMARY KEY ("nif", "roleID")
);

-- Jetons de session : seule l'empreinte SHA-256 du jeton est stockée
CREATE TABLE "Session" (
    "tokenHash" CHAR(64) PRIMARY KEY,
    "nif"       VARCHAR(13) NOT NULL REFERENCES "User"("nif") ON DELETE CASCADE,
    "expireAt"  TIMESTAMPTZ NOT NULL,
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX "Session_nif_idx" ON "Session"("nif");

-- Étape intermédiaire entre le mot de passe et le code TOTP
CREATE TABLE "MfaChallenge" (
    "tokenHash" CHAR(64) PRIMARY KEY,
    "nif"       VARCHAR(13) NOT NULL REFERENCES "User"("nif") ON DELETE CASCADE,
    "expireAt"  TIMESTAMPTZ NOT NULL
);

-- Services protégés par CERBER
CREATE TABLE "Resource" (
    "resourceID"  SERIAL PRIMARY KEY,
    "slug"        VARCHAR(50)  NOT NULL UNIQUE,
    "name"        VARCHAR(100) NOT NULL,
    "url"         VARCHAR(500) NOT NULL,
    "createdAt"   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Rôles autorisés à accéder à une ressource
CREATE TABLE "ResourceRole" (
    "resourceID" INTEGER NOT NULL REFERENCES "Resource"("resourceID") ON DELETE CASCADE,
    "roleID"     INTEGER NOT NULL REFERENCES "Role"("roleID") ON DELETE CASCADE,
    PRIMARY KEY ("resourceID", "roleID")
);

-- Traçabilité des événements d'authentification
CREATE TABLE "AuthEvent" (
    "eventID"   BIGSERIAL PRIMARY KEY,
    "nif"       VARCHAR(13) NULL,
    "type"      VARCHAR(40) NOT NULL,
    "success"   BOOLEAN NOT NULL,
    "ip"        VARCHAR(64) NULL,
    "detail"    VARCHAR(255) NULL,
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX "AuthEvent_createdAt_idx" ON "AuthEvent"("createdAt" DESC);

-- Taux de prélèvement à la source des contribuables (modifié par les agents)
CREATE TABLE "TaxRate" (
    "nif"       VARCHAR(13)  PRIMARY KEY REFERENCES "User"("nif") ON DELETE CASCADE,
    "rate"      NUMERIC(3,1) NOT NULL CHECK ("rate" BETWEEN 0 AND 60),
    "updatedBy" VARCHAR(13)  NULL REFERENCES "User"("nif") ON DELETE SET NULL,
    "updatedAt" TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ==========================================
-- DONNÉES DE DÉMONSTRATION (environnement de dev uniquement)
-- Mots de passe : voir README
-- ==========================================

INSERT INTO "Role" ("name") VALUES
('Administrateur'),
('Agent DGFIP'),
('Contribuable');

INSERT INTO "User" ("nif", "passwordHash", "email", "address", "nbTry", "lockDate") VALUES
('1234567890123', '$argon2id$v=19$m=65536,t=3,p=4$OCeuADxvqGJ+gb3XIXo2tQ$ryZ/TshW9psznXnqd9aTGV3Q3bmT5G4NridMayHNqMU', 'admin.cerber@dgfip.gouv.fr', '', 0, NULL),
('2345678901234', '$argon2id$v=19$m=65536,t=3,p=4$i4janx/VZYY6F4qbcNGyEw$t/M64p3JeJpcgGlq0Jh3Kkl7YbXwl1buFWZkppAZraw', 'agent.dupont@dgfip.gouv.fr', '', 0, NULL),
('3456789012345', '$argon2id$v=19$m=65536,t=3,p=4$c8R7GYoWgpHzbLYNwFWTXg$uJOOCJ40D/DQSj231ozNwnsnScREuiaiEjDli59GQes', 'jean.martin@example.com', '12 rue de la Paix, 75002 Paris', 0, NULL),
('4567890123456', '$argon2id$v=19$m=65536,t=3,p=4$13UY9v07pRacURLe6FqDsw$o6SQQZ7iVHPZW1J3kBX3TwDbRnxMm1pWfb+fxLAwP2I', 'hacker.suspect@example.com', '', 5, now());

INSERT INTO "UserRole" ("nif", "roleID") VALUES
('1234567890123', 1),
('2345678901234', 2),
('3456789012345', 3),
('4567890123456', 3);

INSERT INTO "Resource" ("slug", "name", "url") VALUES
-- Services simulés par les conteneurs svc-* (voir docker-compose.yml).
-- Chemins relatifs : les liens suivent l'adresse utilisée pour ouvrir le portail.
('impots', 'Espace particulier', '/impots/'),
('intranet', 'Intranet DGFIP', '/intranet/'),
('ficoba', 'FICOBA', '/ficoba/'),
-- Page du portail : modification des taux d'imposition
('taux', 'Taux d''imposition', '/taux.html');

INSERT INTO "ResourceRole" ("resourceID", "roleID") VALUES
(1, 2), (1, 3),   -- Espace particulier : agents et contribuables
(2, 1), (2, 2),   -- Intranet : administrateurs et agents
(3, 2),           -- FICOBA : agents uniquement
(4, 2);           -- Taux d'imposition : agents uniquement

INSERT INTO "TaxRate" ("nif", "rate") VALUES
('3456789012345', 7.5),
('4567890123456', 0);
