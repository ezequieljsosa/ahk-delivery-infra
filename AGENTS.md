# AGENTS.md

Guía para quien trabaje en este repositorio, humano o asistente de IA.

## Qué es

`ahk-delivery-infra` es el repositorio central de la maqueta de delivery: levanta el sistema completo con Docker Compose y guarda la documentación que cruza servicios. **No contiene código de negocio**: cada servicio vive en su propio repositorio (`ahk-delivery-catalog-svc`, `-order-svc`, `-courier-svc`, `-predictor`, `-worker`).

## Qué hay acá

- `docker-compose.yml`: usa **solo imágenes** (`ezequieljsosa/ahk-delivery-<servicio>`), nunca `build:`. Las variables `REGISTRY` y `TAG` cambian el origen.
- `build-images.sh`: construye (y con `--push` sube) las imágenes; necesita los repos clonados lado a lado.
- `simulate.py`: crea y entrega pedidos de prueba; solo usa la librería estándar.
- `docs/requirements.md`: requisitos del sistema (`RS-xx`) y diagramas de secuencia de éxito y error.
- `docs/architecture.md`: arquitectura en C4 (Mermaid).
- `postgres/init.sql`, `models/`: inicialización de la base `analytics` y volumen del modelo.

## Comandos

- Levantar: `docker compose up -d`; bajar y borrar datos: `docker compose down -v`.
- Probar el sistema completo: `python3 simulate.py 10` y `docker compose logs worker`.
- Calidad: `pre-commit run --all-files` (ruff sobre `simulate.py`, formato de YAML, etc.).

## Cómo trabajar

- Los requisitos que cruzan servicios se definen **primero** en `docs/requirements.md` y después se bajan a los `specs/` de cada servicio. Si un cambio altera un contrato (REST o eventos), actualizar este repositorio y avisar a los repos afectados.
- Los diagramas describen el comportamiento **actual**; donde hay una limitación, se marca con una nota y se enlaza la feature propuesta que la resuelve.
- Los diagramas Mermaid deben renderizar: probarlos antes de commitear.
- Si cambia el nombre, puerto o variable de un servicio, actualizar el compose, `docs/architecture.md` y los READMEs.

## Reglas

- No agregar `build:` al compose.
- No commitear modelos entrenados (`models/*.joblib`) ni secretos. Las credenciales del compose son de demostración (`ahk/ahk`, `guest/guest`).
- Cada servicio es dueño de su base: no exponer la base de un servicio a otro.
