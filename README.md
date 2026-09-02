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

## Spécifications techniques
* Base de données pour la gestion des utilisateurs -> SQL. 
* Accès au service via une interface web en HTTPS. 
* Création d’un système d’authentification basé sur un jeton. 
* Langages utilisés en Frontend : HTML, CSS, JS 
* Langages utilisés en Backend : FastAPI (Python) 

## Exemples de calls API 

## Hors périmètre 

* Gestion des utilisateurs (LDAP chez le client)
* Creation d'un nouveau compte

Annexe 
* Protection contre les attaques courantes (injection SQL, XSS). 
* Politique de mot de passe : 15 caractères minimum (majuscules, minuscules, caractères spéciaux) selon l'ANSSI (ANSSI-PG-078). 
* S'adapte en temps réel en fonction du nombre d'utilisateurs connectés. 

 
