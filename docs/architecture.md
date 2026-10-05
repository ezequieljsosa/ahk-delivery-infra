# Arquitectura (modelo C4)

Diagramas en [Mermaid C4](https://mermaid.js.org/syntax/c4.html), de lo general a lo particular:
contexto, contenedores y componentes de `order-svc`.

## Nivel 1: contexto

```mermaid
C4Context
    title Contexto: maqueta de delivery de comida

    Person(cliente, "Cliente", "Hace pedidos y recibe el tiempo estimado de entrega")
    Person(repartidor, "Repartidor", "Informa que entregó el pedido y cuánto tardó")
    Person(alumno, "Alumno o docente", "Opera, prueba y extiende el sistema")

    System(delivery, "Maqueta de delivery", "Recibe pedidos, estima el tiempo de entrega, asigna repartidor y procesa el histórico")

    Rel(cliente, delivery, "Hace pedidos", "HTTP / JSON")
    Rel(repartidor, delivery, "Informa entregas", "HTTP / JSON")
    Rel(alumno, delivery, "Consulta, simula pedidos y reentrena el modelo", "HTTP, UI de RabbitMQ, psql")
```

## Nivel 2: contenedores

```mermaid
C4Container
    title Contenedores: maqueta de delivery

    Person(cliente, "Cliente / Repartidor", "Usa la API de pedidos")

    System_Boundary(sistema, "Maqueta de delivery (docker compose)") {
        Container(catalog, "catalog-svc", "Java 21, Spring Boot 4.1", "Restaurantes y menús. Datos: MongoDB 'catalog'")
        Container(order, "order-svc", "Java 21, Spring Boot 4.1", "Crea y entrega pedidos, orquesta a los demás servicios y publica eventos. Datos: PostgreSQL 'orders'")
        Container(courier, "courier-svc", "Java 21, Spring Boot 4.1", "Repartidores y asignación del más cercano. Datos: Redis")
        ContainerQueue(broker, "RabbitMQ", "Exchange topic 'orders'", "order.created, order.delivered")
        Container(predictor, "predictor", "Python, FastAPI, scikit-learn", "Predicción online del ETA. Datos: modelo eta.joblib (volumen)")
        Container(worker, "worker", "Python, pika", "Procesa eventos: histórico y notificaciones. Datos: PostgreSQL 'analytics'")
    }

    Rel(cliente, order, "POST /orders, GET /orders, deliver", "HTTP / JSON")
    Rel(order, catalog, "Consulta restaurante y menú", "HTTP / JSON")
    Rel(order, courier, "Asigna y libera repartidor", "HTTP / JSON")
    Rel(order, predictor, "Pide el ETA", "HTTP / JSON")
    Rel(order, broker, "Publica eventos", "AMQP")
    Rel(broker, worker, "Entrega eventos", "AMQP")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

Datos de cada contenedor (una base por servicio, RNF-02):

| Contenedor | Almacén | Qué guarda |
|---|---|---|
| order-svc | PostgreSQL, base `orders` | Pedidos |
| catalog-svc | MongoDB, base `catalog` | Restaurantes con el menú embebido |
| courier-svc | Redis | Un hash por repartidor y el set de los libres |
| predictor | Archivo `models/eta.joblib` (volumen) | Modelo entrenado, con versión y MAE |
| worker | PostgreSQL, base `analytics` | Tabla `orders_history` |

Notas:

- `orders` y `analytics` comparten la instancia de PostgreSQL pero son bases distintas, y ningún
  servicio usa la del otro.
- **Sincrónico donde se necesita la respuesta** (catálogo, repartidor, ETA); **asincrónico para
  lo que puede esperar** (histórico y notificaciones), de modo que el worker no frena al cliente.
- `order-svc` es el único que habla con los otros servicios: catalog, courier y predictor no se
  conocen entre sí.

### Puertos y accesos

| Contenedor | Puerto | Para qué |
|---|---|---|
| order-svc | 8082 | API de pedidos |
| catalog-svc | 8081 | API de catálogo |
| courier-svc | 8083 | API de repartidores |
| predictor | 8000 | API del modelo (`/docs` muestra Swagger) |
| RabbitMQ | 5672 / 15672 | AMQP / interfaz web (guest/guest) |
| PostgreSQL | 5432 | usuario `ahk`, bases `orders` y `analytics` |
| MongoDB | 27017 | base `catalog` |
| Redis | 6379 | |

## Nivel 3: componentes de order-svc

```mermaid
C4Component
    title Componentes de order-svc

    Container_Ext(catalog, "catalog-svc", "Spring Boot", "Restaurantes y menús")
    Container_Ext(courier, "courier-svc", "Spring Boot", "Repartidores")
    Container_Ext(predictor, "predictor", "FastAPI", "ETA")
    ContainerDb_Ext(ordersdb, "orders", "PostgreSQL", "Pedidos")
    ContainerQueue_Ext(broker, "RabbitMQ", "Exchange 'orders'", "Eventos")

    Container_Boundary(order, "order-svc") {
        Component(controller, "OrderController", "Spring MVC", "Expone /orders y /orders/{id}/deliver")
        Component(service, "OrderService", "Spring", "Orquesta la creación y la entrega del pedido")
        Component(catalogClient, "CatalogClient", "RestClient", "Consulta restaurantes")
        Component(courierClient, "CourierClient", "RestClient", "Asigna y libera repartidores; tolera fallas")
        Component(predictorClient, "PredictorClient", "RestClient", "Pide el ETA; tolera fallas")
        Component(repository, "OrderRepository", "Spring Data JPA", "Persistencia de OrderEntity")
        Component(events, "MessagingConfig + OrderEvent", "Spring AMQP", "Exchange 'orders' y mensajes JSON")
    }

    Rel(controller, service, "Usa")
    Rel(service, catalogClient, "Usa")
    Rel(service, courierClient, "Usa")
    Rel(service, predictorClient, "Usa")
    Rel(service, repository, "Usa")
    Rel(service, events, "Publica")
    Rel(catalogClient, catalog, "GET /restaurants/{id}", "HTTP")
    Rel(courierClient, courier, "POST /couriers/assign, PUT status", "HTTP")
    Rel(predictorClient, predictor, "POST /predict/eta", "HTTP")
    Rel(repository, ordersdb, "Lee y escribe", "JDBC")
    Rel(events, broker, "order.created, order.delivered", "AMQP")
```

## Decisiones de diseño

| Decisión | Motivo |
|---|---|
| Tres tecnologías de base de datos (PostgreSQL, MongoDB, Redis) | Cada una encaja con su dato (pedidos relacionales, menú como documento, disponibilidad efímera) y los alumnos ven los tres modelos. |
| Controllers explícitos (`@RestController`), sin Spring Data REST | La API es un contrato deliberado, no un espejo de las tablas. |
| Predictor y worker en Python | Es donde trabajan los alumnos de ciencia de datos; los de sistemas se concentran en los tres servicios Java. |
| Evento en lugar de llamada directa al worker | El histórico y las notificaciones no deben demorar ni hacer fallar la creación del pedido. |
| Fallas de predictor y repartidor toleradas | El pedido es lo importante; el ETA y el repartidor son mejoras que pueden faltar (RS-02, RS-03). |
| Una imagen por servicio, compose sin `build` | Los alumnos levantan el sistema sin compilar; el laboratorio no tiene internet. |
