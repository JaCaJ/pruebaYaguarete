#!/usr/bin/env bash
# Reconstruye la imagen, aplica migraciones y verifica Django.
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker no está disponible." >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "Falta .env. Copiá .env.example y completá SECRET_KEY y DB_PASSWORD." >&2
  exit 1
fi

echo "Construyendo y levantando servicios..."
docker compose up --build -d

echo "Creando migraciones pendientes..."
docker compose exec -T web python manage.py makemigrations --noinput

echo "Aplicando migraciones..."
docker compose exec -T web python manage.py migrate --noinput

echo "Verificando la configuración..."
docker compose exec -T web python manage.py check

echo "Listo. La app queda en http://localhost:8000/"
