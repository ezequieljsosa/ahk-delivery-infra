# ahk-delivery-infra

Maqueta de **delivery de comida** para el curso. Un cliente hace un pedido, el sistema **predice el tiempo de entrega (ETA)**, le asigna un repartidor y procesa de forma asíncrona las notificaciones y el histórico para analítica.

Este repositorio guarda **todo lo centralizado**: cómo levantar el sistema completo, los requisitos que cruzan servicios y la arquitectura. Cada servicio vive en su propio repositorio.

## Repositorios

| Repositorio | Tecnología | Base de datos | Puerto |
|---|---|---|---|
| [ahk-delivery-infra](https://github.com/ezequieljsosa/ahk-delivery-infra) | Docker Compose, documentación | - | - |
| [ahk-delivery-catalog-svc](https://github.com/ezequieljsosa/ahk-delivery-catalog-svc) | Java, Spring Boot 4.1 | MongoDB | 8081 |
| [ahk-delivery-order-svc](https://github.com/ezequieljsosa/ahk-delivery-order-svc) | Java, Spring Boot 4.1, JPA, AMQP | PostgreSQL (`orders`) | 8082 |
| [ahk-delivery-courier-svc](https://github.com/ezequieljsosa/ahk-delivery-courier-svc) | Java, Spring Boot 4.1 | Redis | 8083 |
| [ahk-delivery-predictor](https://github.com/ezequieljsosa/ahk-delivery-predictor) | Python, FastAPI, scikit-learn | modelo `eta.joblib` | 8000 |
| [ahk-delivery-worker](https://github.com/ezequieljsosa/ahk-delivery-worker) | Python, pika | PostgreSQL (`analytics`) | - |

RabbitMQ: puerto 5672 y consola web en 15672 (guest/guest).

Para trabajar en el código de los servicios, cloná los repositorios uno al lado del otro:

```bash
for r in infra catalog-svc order-svc courier-svc predictor worker; do
  gh repo clone ezequieljsosa/ahk-delivery-$r      # o: git clone https://github.com/ezequieljsosa/ahk-delivery-$r
done
```

## Documentación

- [Requisitos del sistema](docs/requirements.md): requisitos `RS-xx`, flujos con diagramas de secuencia (pedido exitoso, entrega y los casos de error) y trazabilidad hacia los specs de cada servicio.
- [Arquitectura](docs/architecture.md): modelo C4 con Mermaid.
- Diagrama de estados del pedido: está en el [spec 000 de order-svc](https://github.com/ezequieljsosa/ahk-delivery-order-svc/blob/main/specs/000-ciclo-de-vida-del-pedido/spec.md), porque `order-svc` es el dueño del estado. Los requisitos del sistema lo referencian.

GitHub renderiza los diagramas Mermaid directamente.

## Levantarlo

El `docker-compose.yml` no construye nada: usa las imágenes `ezequieljsosa/ahk-delivery-<servicio>:latest` (se cambian con las variables `REGISTRY` y `TAG`).

```bash
docker compose up -d                  # baja las imágenes de Docker Hub si no están en local
python3 simulate.py 20                # crea y entrega 20 pedidos de prueba
docker compose logs -f worker         # ver qué procesa el worker
```

Para construir las imágenes desde el código (necesita todos los repos clonados lado a lado):

```bash
./build-images.sh                     # con --push las sube a Docker Hub (previo `docker login`)
```

Reiniciar de cero (borra los datos): `docker compose down -v`.

## Probarlo a mano

```bash
curl localhost:8081/restaurants                       # catálogo (Mongo)
curl localhost:8083/couriers                          # repartidores (Redis)
curl localhost:8000/model/version                     # versión del modelo

curl -X POST localhost:8082/orders -H 'Content-Type: application/json' -d '{
  "restaurantId": "rest-pizza", "lat": -34.58, "lon": -58.42, "raining": true,
  "items": [{"sku": "PIZZA-MUZA", "qty": 2}]
}'
curl -X POST localhost:8082/orders/1/deliver -H 'Content-Type: application/json' -d '{"actualMinutes": 48}'
```

Mirar los datos directo en cada base:

```bash
docker compose exec postgres psql -U ahk -d analytics -c "select * from orders_history"
docker compose exec mongo mongosh catalog --eval "db.restaurants.find()"
docker compose exec redis redis-cli hgetall courier:<id>
```

## Desarrollo guiado por specs (SDD)

Cada servicio tiene una carpeta `specs/` con una subcarpeta por feature (`NNN-nombre/spec.md`): historia de usuario, requisitos funcionales y escenarios de aceptación. Hay dos clases:

- **Implementado**: describe lo que el servicio ya hace.
- **Propuesto**: todavía no existe. Es la tarea para los alumnos.

Para trabajar una feature: leer su spec, escribir `plan.md` y `tasks.md` en la misma carpeta, implementar con un test por escenario y marcar el spec como implementado. El flujo completo está en el `specs/README.md` de cada servicio.

### Tareas propuestas por perfil

| Perfil | Nivel | Tarea | Spec |
|---|---|---|---|
| Sistemas | ★ | Validar el alta de restaurantes | [catalog-svc 004](https://github.com/ezequieljsosa/ahk-delivery-catalog-svc/tree/main/specs/004-validacion-alta-restaurante) |
| Sistemas | ★★ | Validar el pedido y devolver 400/503 claros | [order-svc 007](https://github.com/ezequieljsosa/ahk-delivery-order-svc/tree/main/specs/007-validacion-de-pedido) |
| Sistemas | ★★ | Validar las transiciones de estado del pedido | [order-svc 008](https://github.com/ezequieljsosa/ahk-delivery-order-svc/tree/main/specs/008-transiciones-validas) |
| Sistemas | ★★ | ETA de reserva cuando falla el predictor | [order-svc 005](https://github.com/ezequieljsosa/ahk-delivery-order-svc/tree/main/specs/005-eta-de-reserva) |
| Sistemas | ★★ | Cancelar un pedido | [order-svc 006](https://github.com/ezequieljsosa/ahk-delivery-order-svc/tree/main/specs/006-cancelar-pedido) |
| Sistemas | ★★ | Desconectar repartidores inactivos (TTL en Redis) | [courier-svc 005](https://github.com/ezequieljsosa/ahk-delivery-courier-svc/tree/main/specs/005-ttl-disponibilidad) |
| Sistemas | ★★★ | Asignación atómica de repartidores | [courier-svc 006](https://github.com/ezequieljsosa/ahk-delivery-courier-svc/tree/main/specs/006-asignacion-atomica) |
| Sistemas | ★★★ | Dead-letter queue en el worker | [worker 004](https://github.com/ezequieljsosa/ahk-delivery-worker/tree/main/specs/004-dead-letter-queue) |
| Sistemas | ★★★ | Publicación confiable de eventos (outbox) | [order-svc 009](https://github.com/ezequieljsosa/ahk-delivery-order-svc/tree/main/specs/009-publicacion-confiable) |
| Data science | ★★ | Reentrenar con datos reales de `orders_history` | [predictor 004](https://github.com/ezequieljsosa/ahk-delivery-predictor/tree/main/specs/004-reentrenar-con-datos-reales) |
| Data science | ★★ | Agregar el día de la semana como feature | [predictor 006](https://github.com/ezequieljsosa/ahk-delivery-predictor/tree/main/specs/006-nueva-feature-dia-de-semana) |
| Data science | ★★ | Reporte del error de predicción | [worker 005](https://github.com/ezequieljsosa/ahk-delivery-worker/tree/main/specs/005-reporte-error-eta) |
| Data science | ★★★ | Segundo predictor: riesgo de cancelación | [predictor 005](https://github.com/ezequieljsosa/ahk-delivery-predictor/tree/main/specs/005-prediccion-de-cancelacion) |
| Data science | ★★★ | Alerta por error alto | [worker 006](https://github.com/ezequieljsosa/ahk-delivery-worker/tree/main/specs/006-alerta-error-alto) |
| Mixta | ★★ | Platos agotados (catálogo y pedidos) | [catalog-svc 005](https://github.com/ezequieljsosa/ahk-delivery-catalog-svc/tree/main/specs/005-platos-agotados) + [order-svc 007](https://github.com/ezequieljsosa/ahk-delivery-order-svc/tree/main/specs/007-validacion-de-pedido) |

## Calidad de código

Cada repositorio trae su `.pre-commit-config.yaml`:

| | Java (`*-svc`) | Python (`predictor`, `worker`, `infra`) |
|---|---|---|
| Formato | google-java-format (AOSP) | `ruff format` |
| Estilo, bugs, seguridad | Checkstyle (`checkstyle.xml`), PMD, SpotBugs (`spotbugs-exclude.xml`) | `ruff check` (reglas en `ruff.toml`) |
| Build | Maven Wrapper (`./mvnw`), toolchains JDK 21, Spring Boot 4.1 | `requirements.txt` |

Una sola vez en la máquina: `pip install pre-commit ruff`. Una sola vez por repositorio: `pre-commit install`.

```bash
# En un repositorio Java
pre-commit run --all-files                         # todo junto
mvn checkstyle:check pmd:check spotbugs:check      # solo el análisis estático

# En un repositorio Python
pre-commit run --all-files                         # o: ruff check . && ruff format --check .
```

Los hooks de Java usan el plugin de toolchains: necesitan un JDK 21 declarado en `~/.m2/toolchains.xml`.

## Laboratorio sin internet

Las VMs de los alumnos no tienen salida a internet. Antes de clonar la plantilla, con conexión, ejecutá en ella `docker compose pull` (o `up -d`): así quedan en local las imágenes de la app y las de infraestructura (PostgreSQL, MongoDB, Redis, RabbitMQ). Para que los alumnos reconstruyan una imagen modificada sin red, ejecutá también `./build-images.sh` en la plantilla y dejá cacheadas las imágenes base (Maven, Temurin, Python). Si agregan una dependencia nueva, hace falta que el docente la deje cacheada antes.

## Licencia

[MIT](LICENSE)
