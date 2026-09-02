# CERBER

## Objectifs

Après avoir subi une cyberattaque sur ses systèmes d'information, la DGFIP a décidé de solliciter notre entreprise afin de développer un nouveau portail d'authentification qui sera utilisé comme SSO sur l'ensemble de ses services. 
CERBER est un système d'authentification qui a pour but de sécuriser l'accès a plusieurs services numériques.


## Spécifications fonctionnelles

Ce portail doit comprendre les fonctionnalités et prérequis suivants :

* Ce système permet une seule authentification pour l'accès à plusieurs ressources informatiques (SSO).
* Système de connexion par numéro fiscal et mot de passe.
* Authentifier les utilisateurs afin de vérifier la légitimité de la demande d'accès à une ressource.
* Mise en place d'une authentification multifacteur « MFA ».
* La demande d'accès à une ressource est vérifiée selon l'identité et le rôle de l'utilisateur (rôle stocké dans la base de données).
* Après 5 tentatives de connexion echouées, le compte est vérouillé.
* L'utilisateur peut réinitialiser son mot de passe. 
* L'utilisateur peut mettre à jour ses informations personnelles (email, adresse postale).
* Traçabilité sur les événements d'authentification : succès, échec, demande de réinitialisation, renouvellement de jetons, MFA.


## Spécifications techniques
* Utilisation de jeton JWT, contenant les informations de chaque utilisateur (identité, rôles)
* Base de données pour la gestion des utilisateurs -> SQL.
* Le MFA est un code aléatoire envoyé par email à l'utilisateur.
* Protection contre les attaques courantes (injection SQL, XSS).
* Politique de mot de passe : 15 caractères minimum (majuscules, minuscules, caractères spéciaux) selon l'ANSSI (ANSSI-PG-078).
* Accès au service via une inteface web en HTTPS.
* S'adapte en temps réel en fonction du nombre d'utilisateurs connectés.
* Langages utilisés en Frontend : HTML, CSS, JS
* Langages utilisés en Backend : FastAPI (Python)


## Hors périmètre 

* Gestion des utilisateurs (LDAP chez le client)
* Creation d'un nouveau compte

