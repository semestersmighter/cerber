FROM nginx:alpine

# openssl : certificat auto-signé créé au premier démarrage (25-cerber-cert.sh)
RUN apk add --no-cache openssl

# La configuration est générée au démarrage à partir de HOST_HEADER, ALLOWED_HOSTS et HTTPS_PORT
COPY nginx.conf.template /etc/nginx/cerber/nginx.conf.template
COPY docker-entrypoint.d/25-cerber-cert.sh docker-entrypoint.d/30-cerber-config.sh /docker-entrypoint.d/
# Retire les fins de ligne Windows (CRLF) éventuelles : sinon les scripts ne démarrent pas
RUN sed -i 's/\r$//' /docker-entrypoint.d/25-cerber-cert.sh /docker-entrypoint.d/30-cerber-config.sh \
      /etc/nginx/cerber/nginx.conf.template \
 && chmod +x /docker-entrypoint.d/25-cerber-cert.sh /docker-entrypoint.d/30-cerber-config.sh

COPY public /usr/share/nginx/html

EXPOSE 80 443
