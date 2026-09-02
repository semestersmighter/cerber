# CERBER

Après avoir subi une cyberattaque sur ses systèmes d'information, la DGFIP a décidé de solliciter notre entreprise afin de développer un nouveau portail d'authentification qui sera utilisé comme SSO sur l'ensemble de ses services. 
CERBER est un système d'authentification qui a pour but de sécuriser l'accès a plusieurs services numériques.


## Objectifs
* Définir un périmètre : Garantir que seules les personnes autorisées accèdent aux services. 
* Permettre à l'utilisateur de gérer lui-même son compte (mot de passe oublié, coordonnées, sécurité).
* Donner aux administrateurs les moyens de gérer les comptes et les droits.
* 

## Spécifications fonctionnelles

Ce portail doit comprendre les fonctionnalités et prérequis suivants :

* Lors de la connexion, un jeton personnel sera délivré pour chaque utilisateur permettant de l'identifier et de définir ses droits.
* Mise en place d'une authentification multifacteur « MFA » (un mail est envoyé à l'utilisateur afin de vérifier son identité).
* Accès au service via une inteface web en HTTPS.
* Politique de mot de passe : 15 caractères minimum (majuscules, minuscules, caractères spéciaux) selon l'ANSSI (ANSSI-PG-078).
* Traçabilité sur les connexions utilisateurs (date, heure, périmètre d'accès).

  

## Spécifications techniques
* Base de données pour la gestion des utilisateurs -> SQL
* S'adapte en temps réel en fonction du nombre d'utilisateurs connectés.
* Langages utilisés en Frontend : HTML, CSS, JS
* Langages utilisés en Backend : FastAPI (Python)


## Hors périmètre 

* Gestion des utilisateurs (LDAP chez le client)
* Creation d'un nouveau compte

