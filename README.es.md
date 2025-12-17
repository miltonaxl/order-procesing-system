# Senior Backend Developer Assessment: Distributed Order Processing System

Este proyecto implementa un sistema de procesamiento de pedidos distribuido utilizando una arquitectura de microservicios, comunicación asíncrona basada en eventos (Saga Pattern) y el stack tecnológico requerido: **Python 3.11+, FastAPI, PostgreSQL y RabbitMQ**.

## Arquitectura y Diseño

El sistema sigue una arquitectura de **Microservicios** con un enfoque de **Eventual Consistency** (Patrón Saga Coreográfico).

### Servicios

| Servicio                 | Responsabilidad                       | Tecnología      | Base de Datos               | Eventos que Publica                         | Eventos a los que se Suscribe                                           |
| :----------------------- | :------------------------------------ | :-------------- | :-------------------------- | :------------------------------------------ | :---------------------------------------------------------------------- |
| **Order Service**        | Gestión de pedidos (API REST).        | FastAPI         | PostgreSQL (`order_db`)     | `OrderCreated`, `OrderCancelled`            | `InventoryUnavailable`, `PaymentProcessed`, `PaymentFailed`             |
| **Inventory Service**    | Gestión de stock y reservas.          | Python Consumer | PostgreSQL (`inventory_db`) | `InventoryReserved`, `InventoryUnavailable` | `OrderCreated`, `OrderCancelled`                                        |
| **Payment Service**      | Simulación de procesamiento de pagos. | Python Consumer | PostgreSQL (`payment_db`)   | `PaymentProcessed`, `PaymentFailed`         | `InventoryReserved`                                                     |
| **Notification Service** | Envío simulado de notificaciones.     | Python Consumer | N/A                         | N/A                                         | `OrderConfirmed`, `OrderCancelled`, `PaymentProcessed`, `PaymentFailed` |

### Flujo de Eventos (Saga Coreográfico)

1.  **Cliente** envía `POST /api/orders` al **Order Service**.
2.  **Order Service** crea el pedido en estado `PENDING` y publica el evento `OrderCreated`.
3.  **Inventory Service** consume `OrderCreated`, verifica el stock y:
    - Si hay stock, reserva el inventario y publica `InventoryReserved`.
    - Si no hay stock, publica `InventoryUnavailable` (lo que lleva a la cancelación del pedido por el Order Service).
4.  **Payment Service** consume `InventoryReserved`, simula el pago (80% de éxito, con reintentos) y publica:
    - `PaymentProcessed` si es exitoso.
    - `PaymentFailed` si falla después de los reintentos.
5.  **Order Service** consume `InventoryUnavailable`, `PaymentProcessed` o `PaymentFailed` y actualiza el estado del pedido a `CANCELLED` o `COMPLETED` respectivamente.
6.  **Notification Service** consume los eventos de estado final (`OrderConfirmed`, `OrderCancelled`, `PaymentProcessed`, `PaymentFailed`) y registra la notificación correspondiente.

## Requisitos Técnicos

- **Monorepo:** Todos los servicios están en carpetas separadas (`order-service`, `inventory-service`, etc.) en la raíz del repositorio.
- **Contenedores:** Se utiliza `docker-compose.yml` para levantar todos los servicios, bases de datos (PostgreSQL) y el Message Queue (RabbitMQ) con un solo comando.
- **Async/Await:** Uso de `async/await` en todo el código I/O (FastAPI, `asyncpg`, `aio-pika`).
- **Persistencia:** Cada servicio con base de datos propia y uso de **Alembic** para migraciones.
- **Idempotencia:** El **Payment Service** utiliza el `order_id` como clave primaria en su tabla de pagos para evitar doble procesamiento.
- **Retry Logic:** El **Payment Service** utiliza la librería `tenacity` con _exponential backoff_ para reintentar el procesamiento de pagos fallidos.

## Configuración y Ejecución

### Prerrequisitos

- Docker y Docker Compose instalados.

### Pasos para Ejecutar

1.  **Clonar el repositorio:**

    ```bash
    git clone <URL_DEL_REPOSITORIO>
    cd order-processing-system
    ```

2.  **Iniciar el sistema:**
    ```bash
    docker-compose up --build
    ```
    Esto construirá las imágenes, iniciará RabbitMQ, las tres bases de datos PostgreSQL y los cuatro microservicios. Los servicios de consumidor (Inventory, Payment, Notification) ejecutarán automáticamente sus migraciones de Alembic y comenzarán a escuchar eventos.

### API Documentation (Order Service)

El **Order Service** expone una API REST en `http://localhost:8000`.

#### 1. Crear un Pedido

**Endpoint:** `POST /api/orders`

**Ejemplo de Request (cURL):**

```bash
curl -X POST http://localhost:8000/api/orders \
-H "Content-Type: application/json" \
-d '{
"customer_id": "customer-123",
"items": [
{"product_id": "product-A", "quantity": 2},
{"product_id": "product-B", "quantity": 1}
],
"total_amount": 150.00
}'
```

**Ejemplo de Response (201 Created):**

```json
{
  "id": "order-uuid-generado",
  "customer_id": "customer-123",
  "items": "[{\"product_id\": \"product-A\", \"quantity\": 2}, {\"product_id\": \"product-B\", \"quantity\": 1}]",
  "total_amount": 150.0,
  "status": "PENDING",
  "created_at": "2025-12-16T10:00:00.000000",
  "updated_at": "2025-12-16T10:00:00.000000"
}
```

#### 2. Consultar Estado del Pedido

**Endpoint:** `GET /api/orders/{order_id}`

**Ejemplo de Request (cURL):**

```bash
curl http://localhost:8000/api/orders/order-uuid-generado
```

**Response:** Devuelve el objeto `OrderRead` con el estado actual (`PENDING`, `COMPLETED`, `CANCELLED`, etc.).

### Guía de Testing (Flujo Completo)

1.  **Inicializar Inventario:** Para que el flujo funcione, el `Inventory Service` ejecuta un script de _seeding_ inicial para poblar la tabla `inventory` con productos y stock.
2.  **Crear Pedido:** Ejecute el `cURL` de creación de pedido.
3.  **Verificar Logs:**
    - Observe los logs del **Order Service** (publicación de `OrderCreated`).
    - Observe los logs del **Inventory Service** (consumo de `OrderCreated`, publicación de `InventoryReserved`).
    - Observe los logs del **Payment Service** (consumo de `InventoryReserved`, simulación de pago, publicación de `PaymentProcessed` o `PaymentFailed`).
    - Observe los logs del **Order Service** (consumo del evento de pago, actualización de estado).
    - Observe los logs del **Notification Service** (consumo del evento de pago, notificación simulada).
4.  **Verificar Estado Final:** Use el `cURL` de consulta para verificar que el estado final del pedido sea `COMPLETED` (si el pago fue exitoso) o `CANCELLED` (si falló).

#### Productos de Prueba (Datos del Seeder)

El inventario se carga automáticamente con los siguientes productos para pruebas:

| Product ID  | Stock Inicial | Escenario de Comportamiento                                                           |
| :---------- | :------------ | :------------------------------------------------------------------------------------ |
| `product-A` | 10            | **Camino Exitoso:** Úsalo para probar reservas exitosas.                              |
| `product-B` | 5             | **Stock Bajo:** Úsalo para probar agotamiento.                                        |
| `product-C` | 0             | **Camino de Fallo:** Úsalo para probar `InventoryUnavailable` y cancelación de orden. |

## Decisiones de Arquitectura Clave

1.  **Patrón Saga Coreográfico:** Se eligió el patrón coreográfico (en lugar de orquestación) para mantener a los servicios más desacoplados. Los servicios reaccionan a los eventos sin un orquestador central, lo que aumenta la resiliencia y la independencia.
2.  **RabbitMQ (aio-pika):** Se seleccionó RabbitMQ por su robustez y soporte para _Exchange Types_ (como `TOPIC`), que es ideal para el patrón de publicación/suscripción requerido. La librería `aio-pika` asegura la compatibilidad con `async/await`.
3.  **Idempotencia en Payment Service:** La clave primaria de la tabla `payments` es el `order_id`. Si el servicio recibe el mismo evento `InventoryReserved` dos veces, el intento de insertar el segundo pago fallará a nivel de base de datos, garantizando que el pago no se procese dos veces.
4.  **Alembic en Dockerfile:** La línea `alembic upgrade head` se ejecuta en el `CMD` de los servicios con base de datos. Esto asegura que la base de datos esté actualizada con el esquema más reciente antes de que el servicio comience a funcionar.

## Testing (Pruebas Unitarias e Integración)

Se han implementado pruebas unitarias para todos los servicios (`Order`, `Inventory`, `Payment`, `Notification`) utilizando `pytest` y `pytest-asyncio`, demostrando la capacidad de:

1.  **Probar la lógica de la API REST** (creación y consulta de pedidos).
2.  **Mocquear dependencias externas** (base de datos y mensajería).
3.  **Probar la lógica crítica del consumidor** (actualización de estado tras evento de pago).

### Cómo Ejecutar las Pruebas Unitarias

1.  Asegúrese de que los contenedores estén levantados (`docker-compose up`).
2.  Ejecute el siguiente comando dentro del contenedor de cada servicio:

```bash
docker exec -it order-service poetry run pytest
docker exec -it inventory-service poetry run pytest
docker exec -it payment-service poetry run pytest
docker exec -it notification-service poetry run pytest
```

### Pruebas de Integración (Flujo Completo)

Se ha implementado una prueba de integración que simula el flujo completo del pedido, incluyendo el escenario de fallo de pago y la transacción compensatoria (rollback de inventario).

**Para ejecutar las pruebas de integración:**

1.  Asegúrese de que todos los servicios estén levantados (`docker-compose up`).
2.  Instale las dependencias de prueba en su entorno local (o en un contenedor de prueba):
    ```bash
    pip install -r tests/requirements.txt
    ```
3.  Ejecute la prueba de integración:
    ```bash
    pytest tests/test_integration.py
    ```

## Cumplimiento del 100% de Requisitos Obligatorios

La solución actual cumple con el 100% de los requisitos obligatorios del test, incluyendo la implementación de la lógica de compensación (rollback) para asegurar la consistencia de los datos en escenarios de fallo distribuido.

| Escenario de Fallo               | Cumplimiento | Detalle de la Solución                                                                                                                                                                                                                                                   |
| :------------------------------- | :----------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1. Inventario Insuficiente**   | **SÍ**       | El **Inventory Service** publica `InventoryUnavailable`, el **Order Service** cancela el pedido y publica `OrderCancelled`. El **Inventory Service** consume `OrderCancelled` y ejecuta la **transacción compensatoria (rollback)**, devolviendo el inventario al stock. |
| **2. Fallo de Pago**             | **SÍ**       | El **Payment Service** publica `PaymentFailed`. El **Order Service** cancela el pedido y publica `OrderCancelled`. El **Inventory Service** consume `OrderCancelled` y ejecuta la **transacción compensatoria (rollback)**, devolviendo el inventario al stock.          |
| **3. Indisponibilidad Temporal** | **SÍ**       | **RabbitMQ** con colas duraderas y `message.process()` asegura que los mensajes se reintenten automáticamente cuando el servicio vuelve a estar disponible.                                                                                                              |
| **4. Eventos Duplicados**        | **SÍ**       | **Idempotencia** implementada en el **Payment Service** usando `order_id` como clave primaria para prevenir doble procesamiento.                                                                                                                                         |
| **5. Fallos Parciales**          | **SÍ**       | **Rollback de Inventario** implementado. El mecanismo de **Retry** de RabbitMQ maneja los fallos temporales de notificación.                                                                                                                                             |

## Bonus Points Implementados

### Resiliencia (Circuit Breaker)

Se ha utilizado la librería `tenacity` en el **Payment Service** para implementar un mecanismo de reintento con _exponential backoff_. Esto actúa como una forma de **Circuit Breaker** simple, previniendo que el servicio de pago colapse ante fallos transitorios y mejorando la robustez del sistema.

## Limitaciones Conocidas y Mejoras Futuras

- **Mecanismo de Timeout de Saga:** Aunque la lógica de compensación está implementada, el patrón coreográfico no incluye un mecanismo de _timeout_ centralizado. Se podría añadir un servicio de **Saga Monitor** para buscar pedidos estancados y forzar la cancelación.
- **Observabilidad Avanzada:** Implementación de _Correlation IDs_ y _Structured Logging_ (p. ej., con `structlog`) para trazabilidad distribuida. (Bonus Point)
- **Seguridad y Rendimiento:** Implementación de API Authentication (JWT), Caching y Database Indexing (Bonus Points).
- **Observabilidad:** Implementación de _Correlation IDs_ y _Structured Logging_ (p. ej., con `structlog`) para trazabilidad distribuida.
