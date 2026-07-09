# Project Sentinel
## Arquitectura del Sistema
Versión: 1.0

### 1. Objetivo
Este documento define la arquitectura técnica de Project Sentinel.
La arquitectura ha sido diseñada para cumplir los siguientes objetivos:
* simplicidad;
* modularidad;
* bajo costo operativo;
* operación continua (24/7);
* facilidad para incorporar nuevas fuentes;
* alta mantenibilidad;
* independencia entre componentes.

La arquitectura describe únicamente la implementación técnica del sistema.
Las reglas del negocio pertenecen al Modelo de Dominio.

### 2. Principios Arquitectónicos

#### 2.1 Monolito Modular
Project Sentinel será implementado como un Monolito Modular.
Esto significa:
* un único repositorio;
* una única aplicación Python;
* un único proceso principal;
* un único contenedor Docker para la aplicación.

La modularidad se obtiene mediante separación clara de responsabilidades y no mediante microservicios.

*Nota sobre el Modelo de Concurrencia:* El término "proceso único" hace referencia estrictamente al empaquetamiento y despliegue físico del sistema, y no al modelo de ejecución interna. Para garantizar la reactividad en tiempo real y evitar bloqueos de I/O de los Collectors, el sistema se implementará utilizando programación asíncrona nativa (`asyncio`). Cada Collector se ejecutará como una tarea asíncrona concurrente no bloqueante compartiendo el mismo proceso principal.

#### 2.2 Arquitectura orientada al dominio
La lógica del negocio reside en el dominio del sistema.
La infraestructura únicamente proporciona servicios para:
* observar fuentes;
* almacenar información;
* enviar notificaciones.

#### 2.3 Collectors desacoplados
Cada fuente de información implementará su propio Collector.
Los Collectors son completamente independientes entre sí.
Agregar una nueva fuente únicamente implica desarrollar un nuevo Collector.

#### 2.4 Una única unidad de información
Toda información que ingresa al sistema se representa mediante una Observation.
No existen formatos especiales según la fuente.
Independientemente de si la información proviene de Woot, Reddit o Telegram, el resto del sistema siempre trabaja con Observations.

#### 2.5 Persistencia completa
Toda Observation será almacenada.
La persistencia no depende de que exista una coincidencia con la Watchlist ni de que se genere una notificación.

#### 2.6 Notificaciones desacopladas
El mecanismo de notificación es independiente del procesamiento.
Durante el MVP únicamente existirá Telegram.
En el futuro podrán incorporarse nuevos canales sin modificar el Processor.

### 3. Arquitectura General
Internet -> (Woot, Reddit, Telegram) -> Collectors -> Processor -> Notification Service -> Telegram
                                                               \-> PostgreSQL

### 4. Componentes

#### 4.1 Collectors
Responsabilidad:
Observar una fuente de información.
Cada Collector únicamente puede:
* conectarse a una fuente;
* obtener nueva información;
* convertirla en Observations;
* entregar las Observations al Processor.

Un Collector nunca:
* consulta PostgreSQL;
* aplica reglas;
* envía notificaciones;
* modifica la Watchlist;
* conoce otros Collectors.

Ejemplos:
* `collectors/woot/`
* `collectors/reddit/`
* `collectors/telegram/`

#### 4.2 Processor
El Processor constituye el núcleo operativo de Sentinel.
Responsabilidades:
* recibir Observations;
* almacenarlas;
* compararlas contra la Watchlist;
* aplicar las reglas del dominio;
* evitar notificaciones duplicadas;
* solicitar el envío de notificaciones.

Toda decisión del sistema ocurre dentro del Processor.

#### 4.3 Notification Service
Su única responsabilidad consiste en entregar notificaciones.
Durante el MVP existirá una única implementación:
`TelegramNotifier`

En el futuro podrán incorporarse:
* Email;
* Discord;
* Push Notifications.
Sin modificar el Processor.

#### 4.4 PostgreSQL
Toda la información persistente será almacenada en PostgreSQL.
Entre ella:
* configuración;
* Watchlist;
* Observations;
* Notifications;
* historial del sistema.

PostgreSQL constituye la única base de datos del proyecto.

### 5. Flujo General
1. Fuente
2. Collector
3. Observation
4. Processor
5. Guardar Observation
6. ¿Coincide con Watchlist? (No -> Fin)
7. Sí -> Crear Notification
8. Notification Service
9. Telegram

### 6. Organización del Proyecto
project-sentinel/
├── app/
│   ├── domain/
│   │   ├── entities/
│   │   ├── services/
│   │   └── rules/
│   ├── collectors/
│   │   ├── woot/
│   │   ├── reddit/
│   │   └── telegram/
│   └── infrastructure/
│       ├── database/
│       ├── notifications/
│       ├── logging/
│       └── configuration/
├── tests/
├── docker/
└── main.py

La estructura busca separar claramente:
* dominio;
* infraestructura;
* integración con fuentes externas.

### 7. Despliegue
El MVP utilizará Docker Compose.
* `sentinel`
* `postgres`

No existirán:
* microservicios;
* colas de mensajes;
* balanceadores;
* componentes distribuidos.

Toda la lógica reside dentro de Sentinel.

### 8. Dependencias
Las dependencias entre componentes siempre tendrán la siguiente dirección:
* Collectors -> Processor -> Notification Service -> Telegram
* Processor -> PostgreSQL

Nunca al contrario. Esto garantiza un bajo acoplamiento entre los módulos.

### 9. Seguridad
Durante el MVP se adoptarán las siguientes medidas:
* todas las credenciales se almacenarán mediante variables de entorno;
* ningún secreto se incluirá en el código fuente;
* PostgreSQL únicamente será accesible desde Docker Compose;
* Sentinel no expondrá puertos públicos hacia Internet;
* Telegram se utilizará únicamente mediante conexiones salientes hacia su API.

Esto reduce significativamente la superficie de ataque del sistema.

### 10. Escalabilidad
La arquitectura permite incorporar nuevas fuentes sin modificar el Processor.
Ejemplos:
* `collectors/ebay/`
* `collectors/walmart/`
* `collectors/rss/`
* `collectors/discord/`
* `collectors/bluesky/`

Cada nuevo módulo únicamente deberá implementar el contrato definido para un Collector.

### 11. Evolución
La arquitectura ha sido diseñada para admitir futuras extensiones sin modificar el núcleo del sistema.
Ejemplos:
* nuevos Collectors;
* nuevos canales de notificación;
* panel web;
* API REST;
* comandos mediante Telegram.

Estas capacidades no forman parte del MVP y no afectan la implementación inicial.