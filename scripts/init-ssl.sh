#!/bin/bash
# Run ONCE on VPS before first deploy with SSL.
# Usage: ./scripts/init-ssl.sh yourdomain.com your@email.com
set -e

DOMAIN=$1
EMAIL=$2

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
  echo "Usage: $0 <domain> <email>"
  exit 1
fi

cd /opt/interhack-2026

# 1. Start nginx on HTTP only (before SSL cert exists)
#    Temporarily use a minimal config that only serves certbot challenge
cat > /tmp/nginx-init.conf << EOF
server {
    listen 80;
    server_name $DOMAIN;
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    location / {
        return 200 'ok';
    }
}
EOF

docker run -d --name nginx-init \
  -p 80:80 \
  -v /tmp/nginx-init.conf:/etc/nginx/conf.d/default.conf:ro \
  -v interhack-2026_certbot_webroot:/var/www/certbot \
  nginx:alpine

# 2. Get certificate
docker run --rm \
  -v interhack-2026_certbot_certs:/etc/letsencrypt \
  -v interhack-2026_certbot_webroot:/var/www/certbot \
  certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"

# 3. Stop temp nginx
docker stop nginx-init && docker rm nginx-init

# 4. Replace DOMAIN placeholder in nginx.conf
sed -i "s/DOMAIN/$DOMAIN/g" /opt/interhack-2026/nginx/nginx.conf

echo "SSL ready for $DOMAIN. Now run the GitHub Actions deploy or:"
echo "  docker compose -f docker-compose.prod.yml --env-file .env.prod up -d"
