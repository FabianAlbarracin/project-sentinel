# 03 - Domain Model.md

# Project Sentinel
## Modelo de Dominio

**Versión:** 1.0

---

# 1. Objetivo

Este documento define el lenguaje del dominio utilizado por Project Sentinel.

Su propósito es establecer una definición única para cada concepto del sistema, de forma que toda la implementación, la arquitectura y la base de datos utilicen el mismo vocabulario.

El dominio debe permanecer independiente de cualquier tecnología utilizada para implementarlo.

---

# 2. Filosofía del Dominio

Project Sentinel no está centrado en tiendas.

Tampoco está centrado en web scraping.

Project Sentinel está centrado en **observar información relacionada con productos definidos por el usuario**.

Las fuentes únicamente producen información.

El sistema decide si esa información resulta relevante.

---

# 3. Principios del Dominio

## 3.1 El usuario define el interés

El usuario decide qué desea monitorear.

Sentinel nunca decide qué productos son importantes.

---

## 3.2 Las fuentes únicamente observan

Una fuente nunca interpreta información.

Únicamente publica contenido.

---

## 3.3 Toda información observada se registra

Toda Observation será almacenada.

Genere o no una Notification.

---

## 3.4 El Processor concentra la lógica

Toda decisión pertenece al Processor.

Los demás componentes únicamente colaboran con él.

---

## 3.5 El dominio es independiente

El dominio nunca depende de:

- PostgreSQL
- Docker
- Telegram
- Reddit
- Woot
- APIs
- librerías externas

Estas pertenecen a la infraestructura.

---

# 4. Conceptos del Dominio

## 4.1 Watchlist

La Watchlist representa el conjunto de intereses definidos por el usuario.

Todo el sistema gira alrededor de esta colección.

Ejemplo

```
Kindle

Steam Deck

Framework Laptop
```

---

## 4.2 Watch Item

Representa un elemento específico de la Watchlist.

Ejemplos

- Kindle
- Kindle Paperwhite
- Steam Deck

Un Watch Item no pertenece a ninguna tienda.

Es un concepto completamente independiente de la fuente donde aparezca.

---

## 4.3 Watch Term

Un Watch Item está compuesto por uno o más términos utilizados para determinar si una Observation está relacionada con él.

Existen dos tipos.

### ANCHOR

Son términos cuya presencia indica una posible coincidencia.

Ejemplos

```
kindle

paperwhite

scribe
```

Una Observation únicamente podrá asociarse a un Watch Item si contiene al menos un término ANCHOR.

---

### EXCLUDE

Son términos que invalidan una coincidencia.

Ejemplos

```
case

cover

protector

skin

sleeve
```

Su objetivo es reducir falsos positivos.

Ejemplo

```
Kindle Case
```

Aunque contiene el término "kindle", será descartado porque también contiene "case".

---

## 4.4 Source

Una Source representa cualquier origen de información.

Ejemplos

- Woot
- Reddit
- Telegram

Todas las Sources tienen exactamente la misma importancia dentro del sistema.

Una Source nunca contiene lógica del negocio.

---

## 4.5 Collector

Un Collector observa una única Source.

Su única responsabilidad consiste en:

- obtener nueva información;
- convertirla en Observations;
- entregarlas al Processor.

Un Collector nunca:

- consulta PostgreSQL;
- aplica reglas;
- envía notificaciones;
- modifica la Watchlist;
- conoce otros Collectors.

---

## 4.6 Observation

La Observation constituye la unidad fundamental del dominio.

Representa el hecho de que una Source publicó determinada información en un instante específico.

Una Observation no afirma que la información sea correcta.

Únicamente registra que fue observada.

Ejemplos

- Nuevo Kindle publicado.
- Cupón encontrado.
- Publicación en Reddit.
- Mensaje en Telegram.

Una Observation nunca se modifica.

---

## 4.7 Processor

El Processor representa el núcleo operativo del dominio.

Es el único componente autorizado para tomar decisiones.

Responsabilidades

- almacenar Observations;
- compararlas con la Watchlist;
- aplicar las reglas del dominio;
- determinar si debe generarse una Notification;
- evitar notificaciones duplicadas.

Toda la inteligencia del sistema reside en este componente.

---

## 4.8 Rule

Una Rule representa un criterio utilizado por el Processor para evaluar una Observation.

Ejemplos

- contiene un término ANCHOR;
- contiene un término EXCLUDE;
- corresponde a un Watch Item;
- ya fue notificada anteriormente.

Las Rules nunca pertenecen a un Collector.

---

## 4.9 Notification

Una Notification representa un mensaje enviado al usuario.

Siempre proviene de una Observation previamente registrada.

Una Notification nunca se genera directamente desde un Collector.

Durante el MVP únicamente existirá Telegram como canal de notificación.

---

# 5. Relaciones del Dominio

```text
                 Watchlist

                     │

               contiene

                     │

                Watch Items

                     │

               definidos por

                     │

               Watch Terms

                     │

             evalúan una

                     │

               Observation

                     ▲

                     │

             producida por

                     │

                 Collector

                     ▲

                     │

                  Source

                     │

                     ▼

                 Processor

                     │

             aplica Rules

                     │

                     ▼

              Notification
```

---

# 6. Flujo del Dominio

```text
Source

↓

Collector

↓

Observation

↓

Processor

↓

Guardar Observation

↓

Aplicar Rules

↓

¿Generar Notification?

↓

Sí

↓

Notification
```

---

# 7. Límites del Dominio

No pertenecen al dominio:

- Docker Compose;
- PostgreSQL;
- SQLAlchemy;
- API de Telegram;
- API de Reddit;
- API de Woot;
- Web Scraping;
- Requests;
- BeautifulSoup;
- Playwright.

Estas tecnologías implementan el dominio, pero no forman parte de él.

---

# 8. Invariantes del Dominio

Las siguientes reglas siempre deben cumplirse.

### Una Observation pertenece a una única Source.

---

### Una Observation nunca se modifica.

---

### Toda Observation se almacena.

---

### Una Notification siempre proviene de una Observation.

---

### Los Collectors nunca toman decisiones.

---

### El Processor es el único componente que aplica Rules.

---

### La Watchlist es definida exclusivamente por el usuario.

---

# 9. Evolución del Modelo

El modelo permite incorporar sin modificaciones conceptuales:

- nuevos Watch Items;
- nuevos Collectors;
- nuevas Sources;
- nuevos canales de notificación;
- nuevas Rules.

La incorporación de cualquiera de estos elementos no altera los conceptos fundamentales del dominio.

---

# 10. Glosario

| Concepto         | Definición                                                           |
| ---------------- | -------------------------------------------------------------------- |
| **Watchlist**    | Conjunto de productos que el usuario desea monitorear.               |
| **Watch Item**   | Producto o categoría específica dentro de la Watchlist.              |
| **Watch Term**   | Término utilizado para identificar o descartar Observations.         |
| **Source**       | Origen de información observado por Sentinel.                        |
| **Collector**    | Componente que observa una Source y genera Observations.             |
| **Observation**  | Registro inmutable de información observada.                         |
| **Processor**    | Núcleo del sistema que aplica las reglas del dominio.                |
| **Rule**         | Criterio utilizado para evaluar una Observation.                     |
| **Notification** | Mensaje enviado al usuario cuando una Observation resulta relevante. |