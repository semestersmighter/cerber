FROM nginx:alpine

# Certificat TLS auto-signé pour le développement
RUN apk add --no-cache openssl \
 && mkdir -p /etc/nginx/certs \
 && openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
      -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" \
      -keyout /etc/nginx/certs/cerber.key -out /etc/nginx/certs/cerber.crt

# La configuration est générée au démarrage à partir de HOST_HEADER, ALLOWED_HOSTS et HTTPS_PORT
COPY nginx.conf.template /etc/nginx/cerber/nginx.conf.template
COPY docker-entrypoint.d/30-cerber-config.sh /docker-entrypoint.d/30-cerber-config.sh
# Retire les fins de ligne Windows (CRLF) éventuelles : sinon le script ne démarre pas
RUN sed -i 's/\r$//' /docker-entrypoint.d/30-cerber-config.sh /etc/nginx/cerber/nginx.conf.template \
 && chmod +x /docker-entrypoint.d/30-cerber-config.sh

COPY public /usr/share/nginx/html

EXPOSE 80 443
