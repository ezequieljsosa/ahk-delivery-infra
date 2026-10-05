#!/usr/bin/env bash
# Construye las imágenes de la app y las etiqueta como las espera docker-compose.yml.
# Requiere tener los repositorios ahk-delivery-* clonados uno al lado del otro (este script
# está en ahk-delivery-infra/ y busca a sus hermanos en el directorio padre).
#
# Uso:  ./build-images.sh           (solo construye, queda en tu docker local)
#       ./build-images.sh --push    (además las sube a Docker Hub; requiere `docker login`)
# Variables: REGISTRY (default ezequieljsosa), TAG (default latest)
set -euo pipefail
cd "$(dirname "$0")/.."

REGISTRY="${REGISTRY:-ezequieljsosa}"
TAG="${TAG:-latest}"

for svc in catalog-svc courier-svc order-svc predictor worker; do
  image="$REGISTRY/ahk-delivery-$svc:$TAG"
  echo "== construyendo $image"
  docker build --tag "$image" "ahk-delivery-$svc"
  if [[ "${1:-}" == "--push" ]]; then
    docker push "$image"
  fi
done
