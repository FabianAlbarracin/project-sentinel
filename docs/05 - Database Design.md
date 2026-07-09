# Project Sentinel
## Database Design
Versión: 1.0

### 1. Objetivo
Este documento define el modelo relacional de datos utilizado por Project Sentinel.
La base de datos tiene cinco objetivos principales:
* almacenar la configuración del sistema;
* almacenar la Watchlist;
* registrar todas las Observations;
* registrar todas las Notifications enviadas;
* conservar un historial completo de ejecución.

La base de datos no pretende convertirse en un catálogo de productos ni en una plataforma de comercio electrónico.
Su responsabilidad consiste únicamente en almacenar la información necesaria para operar Sentinel.

### 2. Principios de Diseño

#### 2.1 Simplicidad
Cada tabla representa un único concepto del dominio.

#### 2.2 Observations Inmutables
Una Observation nunca será modificada.
Si una fuente publica información diferente, Sentinel creará una nueva Observation.
Las Observations únicamente permiten operaciones INSERT.

#### 2.3 Todo se registra
Toda Observation será almacenada.
Genere o no una Notification.

#### 2.4 Relaciones explícitas
Todas las relaciones se implementarán mediante claves foráneas.
No se utilizarán estructuras embebidas ni listas dentro de una columna.

#### 2.5 Modelo normalizado
El modelo busca minimizar duplicidad de información manteniendo un diseño sencillo y fácil de mantener.

### 3. Modelo Entidad-Relación
* Sources
* Observations
* Notifications
* Watch Items
* Watch Terms
* Settings

### 4. Tabla: sources
Representa cada fuente de información observada por Sentinel.

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| id | PK | Identificador |
| name | VARCHAR | Nombre de la fuente |
| enabled | BOOLEAN | Fuente habilitada |
| created_at | TIMESTAMP | Fecha de creación |

Ejemplo:
* 1, Woot
* 2, Reddit
* 3, Telegram

### 5. Tabla: watch_items
Representa un elemento definido por el usuario dentro de la Watchlist.
Ejemplos:
* Kindle
* Steam Deck
* Framework Laptop

| Campo | Tipo |
| :--- | :--- |
| id | PK |
| name | VARCHAR |
| enabled | BOOLEAN |
| created_at | TIMESTAMP |

### 6. Tabla: watch_terms
Define las reglas mínimas utilizadas por el Processor para identificar una Observation relacionada con un Watch Item.

| Campo | Tipo |
| :--- | :--- |
| id | PK |
| watch_item_id | FK |
| term | VARCHAR |
| term_type | VARCHAR |
| created_at | TIMESTAMP |

Tipos de término:
**ANCHOR**
Al menos un término ANCHOR debe aparecer en la Observation para que pueda considerarse relacionada con el Watch Item.
Ejemplos: kindle, paperwhite, scribe.

**EXCLUDE**
Si aparece un término EXCLUDE, la Observation será descartada para ese Watch Item.
Ejemplos: case, cover, protector, skin, sleeve.

Restricción:
No puede existir el mismo término dos veces para un mismo Watch Item.
UNIQUE (watch_item_id, term)

### 7. Tabla: observations
Es la entidad principal del sistema. Cada fila representa una Observation generada por un Collector.

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| id | PK | Identificador único de la observación |
| source_id | FK | Fuente donde fue observada la información |
| watch_item_id | FK NULL | Watch Item con el que coincidió (puede ser NULL) |
| external_id | VARCHAR NULL | Identificador nativo y estable provisto por la Source externa |
| observed_at | TIMESTAMP | Fecha y hora original de la publicación |
| observation_type | VARCHAR | Valores permitidos: PRODUCT, COUPON, POST, UNKNOWN |
| title | TEXT | Título detectado por el Collector |
| price | DECIMAL NULL | Precio encontrado (puede ser NULL) |
| currency | VARCHAR NULL | Moneda detectada (Ej: USD, EUR, COP) |
| coupon | VARCHAR NULL | Código de descuento (puede ser NULL) |
| url | TEXT | Enlace hacia la publicación original |
| raw_content | TEXT | Contenido original recibido por el Collector |
| created_at | TIMESTAMP | Fecha en la que Sentinel almacenó la Observation |

#### Descripción de campos adicionales:
* **external_id:** Representa el identificador único persistente que cada Source asigne a la publicación (por ejemplo: el ID de un post en Reddit, el message_id en un canal de Telegram, o el ID de producto en la API de Woot). El Processor utilizará de forma prioritaria este campo para ejecutar la lógica de deduplicación, evitando falsos positivos derivados de URLs con parámetros dinámicos o ligeros cambios de texto en los títulos.

### 8. Tabla: notifications
Registra todas las notificaciones enviadas.

| Campo | Tipo |
| :--- | :--- |
| id | PK |
| observation_id | FK |
| channel | VARCHAR |
| status | VARCHAR |
| sent_at | TIMESTAMP |

Ejemplos:
* channel: Telegram
* status: SUCCESS, FAILED

### 9. Tabla: settings
Configuración general del sistema.

| Campo | Tipo |
| :--- | :--- |
| key | PK |
| value | TEXT |

#### Ejemplos de claves requeridas:
* `telegram_bot_token`
* `telegram_chat_id`
* `woot_interval_seconds`
* `reddit_interval_seconds`
* `telegram_enabled`
* `retention_days`: Define la cantidad de días que se conservarán las observaciones en la base de datos antes de una purga masiva. Por defecto se establecerá con un valor `NULL` (infinito), asegurando el cumplimiento estricto del principio de persistencia histórica completa del sistema.

### 10. Relaciones
* sources (1) -> (N) observations
* watch_items (1) -> (N) watch_terms
* watch_items (1) -> (N) observations (Opcional)
* observations (1) -> (N) notifications

### 11. Restricciones
* **Sources:** El nombre debe ser único. UNIQUE(name)
* **Watch Items:** El nombre debe ser único. UNIQUE(name)
* **Watch Terms:** No puede repetirse un término dentro del mismo Watch Item.
* **Observations:** Nunca podrán modificarse. Únicamente permiten INSERT.
* **Notifications:** Toda Notification debe pertenecer a una Observation.

### 12. Índices
* `observations`: source_id, watch_item_id, observed_at, observation_type
* `watch_terms`: watch_item_id, term
* `notifications`: observation_id

### 13. Flujo de Persistencia
Internet -> Collector -> Observation -> INSERT Observation -> Processor -> ¿Coincide con Watchlist? (NO -> Fin) / (SI -> Crear Notification -> INSERT Notification -> Telegram)

### 14. Decisiones de Diseño
No se crearán tablas para:
* productos;
* marcas;
* fabricantes;
* modelos;
* categorías;
* precios históricos;
* inventario.

Estas entidades no forman parte del objetivo del MVP.
Sentinel observa información. No administra un catálogo de productos.

### 15. Evolución
El modelo permite incorporar nuevos Collectors sin modificar la estructura de la base de datos.
Ejemplos:
* RSS;
* Discord;
* Blogs;
* eBay.

Todos producirán nuevas Observations utilizando exactamente el mismo modelo relacional.
La evolución del sistema deberá preservar siempre la simplicidad del modelo de datos.

Nota: Los atributos específicos de una fuente (por ejemplo, variantes, colores o múltiples precios) no formarán parte del modelo del MVP hasta conocer el formato real de los datos proporcionados por dicha fuente. El modelo se ampliará únicamente cuando exista una necesidad demostrada.