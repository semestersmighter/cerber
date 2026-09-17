-- ==========================================
-- CREATION DU SCHEMA
-- ==========================================

CREATE TABLE "Role" (
    "roleID" SERIAL PRIMARY KEY,
    "name" VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE "User" (
    "nif" VARCHAR(13) PRIMARY KEY,
    "passwordHash" VARCHAR(255) NOT NULL,
    "email" VARCHAR(255) NOT NULL UNIQUE,
    "nbTry" INTEGER DEFAULT 0,
    "lockDate" TIMESTAMP NULL
);

-- Table de liaison pour autoriser plusieurs rôles par utilisateur
CREATE TABLE "UserRole" (
    "nif" VARCHAR(13) NOT NULL,
    "roleID" INTEGER NOT NULL,
    PRIMARY KEY ("nif", "roleID"),
    CONSTRAINT fk_ur_user FOREIGN KEY ("nif") REFERENCES "User"("nif") ON DELETE CASCADE,
    CONSTRAINT fk_ur_role FOREIGN KEY ("roleID") REFERENCES "Role"("roleID") ON DELETE CASCADE
);

CREATE TABLE "Session" (
    "sessionToken" VARCHAR(255) PRIMARY KEY,
    "nif" VARCHAR(13) NOT NULL UNIQUE,
    "expireAt" TIMESTAMP NOT NULL,
    "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user_session FOREIGN KEY ("nif") REFERENCES "User"("nif") ON DELETE CASCADE
);

-- ==========================================
-- INSERTION DES DONNEES FICTIVES
-- ==========================================

-- Création des rôles
INSERT INTO "Role" ("name") VALUES
('Administrateur'),
('Agent DGFIP'),
('Contribuable');

-- Création des utilisateurs
INSERT INTO "User" ("nif", "passwordHash", "email", "nbTry", "lockDate") VALUES
('1234567890123', '$argon2id$v=19$m=65536,t=3,p=4$pd6ISI7iLPAbYE280Grjlg$hZpZReMvY6sRRHCGAmmptVjMfeXH1RISkcGr5WhAXbo', 'admin.cerber@dgfip.gouv.fr', 0, NULL),
('2345678901234', '$argon2id$v=19$m=65536,t=3,p=4$xkW4bB1O8kdg0ZGgEgSenA$Mgo03FELTSSh08Wz5J3maHKqKVAhvpztBnyAIkh9ifE', 'agent.dupont@dgfip.gouv.fr', 0, NULL),
('3456789012345', '$argon2id$v=19$m=65536,t=3,p=4$WdN7PQln2bToPvA7MjWpRA$gg9nnmYOFsQCDRIsrE0IDiwTMi0iUH8opEnORSYyjpU', 'jean.martin@example.com', 0, NULL),
('4567890123456', '$argon2id$v=19$m=65536,t=3,p=4$bZs1lPg+P0sJamYWMwlrAg$adoMTPaB5rrSxQKDEav3ILoJML6T8/ggV7BZRIIrb8U', 'hacker.suspect@example.com', 5, CURRENT_TIMESTAMP);

-- Attribution des rôles aux utilisateurs (Multi-rôles possible)
INSERT INTO "UserRole" ("nif", "roleID") VALUES
('1234567890123', 1), -- Admin.Cerber : Administrateur
('2345678901234', 2), -- Agent.Dupont : Agent DGFIP
('3456789012345', 3), -- Jean.Martin : Contribuable
('4567890123456', 3); -- Hacker.Suspect : Contribuable

-- Création des sessions actives
INSERT INTO "Session" ("sessionToken", "nif", "expireAt", "createdAt") VALUES
('token_azertyuiop1234567890', '1234567890123', CURRENT_TIMESTAMP + INTERVAL '2 hours', CURRENT_TIMESTAMP),
('token_qsdfghjklm0987654321', '2345678901234', CURRENT_TIMESTAMP + INTERVAL '1 hour', CURRENT_TIMESTAMP);