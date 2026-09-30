#!/bin/sh
# Crée un certificat TLS auto-signé au premier démarrage si aucun n'est fourni.
# Généré ici plutôt qu'à la construction : l'image publiée ne contient aucune clé privée,
# chaque installation a la sienne. Pour un vrai certificat, monter cerber.crt et cerber.key
# dans /etc/nginx/certs.
set -eu

CERT_DIR=/etc/nginx/certs

if [ -s "$CERT_DIR/cerber.crt" ] && [ -s "$CERT_DIR/cerber.key" ]; then
  exit 0
fi

mkdir -p "$CERT_DIR"
openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
  -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" \
  -keyout "$CERT_DIR/cerber.key" -out "$CERT_DIR/cerber.crt" 2>/dev/null
chmod 600 "$CERT_DIR/cerber.key"
echo "cerber: certificat auto-signé créé dans $CERT_DIR"
