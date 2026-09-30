#!/bin/sh
# Génère /etc/nginx/conf.d/default.conf à partir du modèle et des variables d'environnement.
# Exécuté automatiquement par l'entrypoint de l'image nginx officielle.
set -eu
set -f  # pas d'expansion de "*" par le shell

TEMPLATE="${CERBER_TEMPLATE:-/etc/nginx/cerber/nginx.conf.template}"
OUTPUT="${CERBER_OUTPUT:-/etc/nginx/conf.d/default.conf}"

HOST_HEADER="$(printf '%s' "${HOST_HEADER:-host}" | tr 'A-Z' 'a-z')"
ALLOWED_HOSTS="${ALLOWED_HOSTS:-*}"
HTTPS_PORT="${HTTPS_PORT:-443}"

fail() { echo "cerber: $*" >&2; exit 1; }

# En-tête source du nom d'hôte public
case "$HOST_HEADER" in
  host)             HOST_SOURCE='$host' ;;
  x-forwarded-host) HOST_SOURCE='$http_x_forwarded_host' ;;
  *) fail "HOST_HEADER doit valoir 'host' ou 'x-forwarded-host' (reçu : $HOST_HEADER)" ;;
esac

# Règles de la map $host_allowed
RULES=""
ALLOW_ALL=0
for entry in $(printf '%s' "$ALLOWED_HOSTS" | tr ',' ' '); do
  entry="$(printf '%s' "$entry" | tr 'A-Z' 'a-z')"
  case "$entry" in
    '*')   ALLOW_ALL=1; continue ;;
  esac
  # Seuls les caractères d'un nom d'hôte sont acceptés (pas d'injection dans la config)
  printf '%s' "$entry" | grep -Eq '^(\*\.)?[a-z0-9]([a-z0-9.-]*[a-z0-9])?$' \
    || fail "ALLOWED_HOSTS : valeur invalide '$entry'"
  case "$entry" in
    '*.'*) suffix="$(printf '%s' "${entry#\*}" | sed 's/\./\\./g')"
           RULES="${RULES}    \"~*^[^:]+${suffix}\$\" 1;
" ;;
    *)     RULES="${RULES}    \"$entry\" 1;
" ;;
  esac
done
if [ "$ALLOW_ALL" = 1 ]; then
  RULES="    default 1;
"
else
  [ -n "$RULES" ] || fail "ALLOWED_HOSTS est vide"
  RULES="    default 0;
$RULES"
fi

# Port dans la redirection HTTP -> HTTPS (omis pour 443)
printf '%s' "$HTTPS_PORT" | grep -Eq '^[0-9]{1,5}$' || fail "HTTPS_PORT invalide : $HTTPS_PORT"
if [ "$HTTPS_PORT" = "443" ]; then PORT_SUFFIX=""; else PORT_SUFFIX=":$HTTPS_PORT"; fi

# Remplacement des marqueurs (les règles multi-lignes passent par awk)
awk -v src="$HOST_SOURCE" -v rules="$RULES" -v port="$PORT_SUFFIX" '
  /@@HOST_RULES@@/ { printf "%s", rules; next }
  { gsub(/@@HOST_SOURCE@@/, src); gsub(/@@HTTPS_PORT_SUFFIX@@/, port); print }
' "$TEMPLATE" > "$OUTPUT"

echo "cerber: HOST_HEADER=$HOST_HEADER ALLOWED_HOSTS=$ALLOWED_HOSTS HTTPS_PORT=$HTTPS_PORT"
