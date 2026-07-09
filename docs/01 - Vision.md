# 01 - Vision.md

# Project Sentinel
## Visión del Proyecto

**Versión:** 1.0

---

# Misión

> **Project Sentinel actúa como un observador permanente de Internet para los productos definidos por el usuario, registrando cada observación relevante y notificando las oportunidades de compra con la menor latencia posible.**

Sentinel observa y notifica.

No compra, no decide y no valida la información publicada por terceros.

---

# 1. Propósito

Project Sentinel es una plataforma personal de monitoreo de oportunidades cuyo objetivo es detectar, registrar y notificar en tiempo real información relacionada con productos de interés definidos por el usuario.

El sistema observa múltiples fuentes de información, centraliza las observaciones detectadas y mantiene un historial completo para futuras consultas y análisis.

---

# 2. Problema que Resuelve

Las oportunidades de compra aparecen distribuidas en múltiples fuentes independientes.

Por ejemplo:

- Woot publica un nuevo producto.
- Reddit comparte un cupón.
- Un grupo de Telegram descubre una oferta.
- Otra comunidad publica una promoción diferente para el mismo producto.

Actualmente el usuario debe revisar manualmente todas estas fuentes para evitar perder oportunidades.

Project Sentinel automatiza esta tarea y concentra toda la información relevante en un único punto de notificación.

---

# 3. Objetivo Principal

Detectar cualquier observación relacionada con los productos definidos por el usuario y notificarla en el menor tiempo posible.

La prioridad del sistema es reducir al mínimo la latencia entre la publicación de una observación y la notificación enviada al usuario.

---

# 4. Identidad del Proyecto

Project Sentinel está centrado en los productos que interesan al usuario.

No está centrado en tiendas, comunidades o servicios específicos.

Las fuentes de información únicamente representan lugares donde pueden aparecer observaciones relacionadas con los elementos de la Watchlist.

La incorporación o eliminación de una fuente nunca debe modificar el funcionamiento del núcleo del sistema.

---

# 5. Principios del Proyecto

## 5.1 El usuario define qué es importante

Sentinel nunca decide qué productos debe monitorear.

El usuario define una Watchlist y el sistema observa Internet buscando información relacionada con ella.

---

## 5.2 Las fuentes únicamente publican información

Las tiendas, comunidades y servicios externos no contienen lógica del negocio.

Su única función consiste en producir información que puede resultar relevante para el usuario.

---

## 5.3 Sentinel registra observaciones

El sistema registra que una fuente publicó determinada información.

No intenta verificar automáticamente:

- si un cupón funciona;
- si una oferta continúa disponible;
- si un producto sigue teniendo inventario;
- si una publicación es verdadera.

La interpretación corresponde al usuario.

---

## 5.4 La velocidad tiene prioridad

Las oportunidades suelen tener una duración limitada.

Reducir el tiempo entre la publicación de una observación y la notificación es uno de los objetivos principales del proyecto.

---

## 5.5 Toda observación queda registrada

Todas las observaciones detectadas serán almacenadas, independientemente de que generen o no una notificación.

El historial constituye uno de los principales activos del sistema.

---

## 5.6 Bajo costo operativo

Sentinel debe poder operar utilizando principalmente:

- software libre;
- infraestructura propia;
- APIs gratuitas cuando existan;
- servicios autoalojados.

El proyecto evitará depender de servicios con costos mensuales para su funcionamiento normal.

---

## 5.7 Simplicidad antes que complejidad

El MVP resolverá únicamente el problema principal.

Toda funcionalidad adicional deberá justificar claramente el valor que aporta antes de incorporarse al proyecto.

---

# 6. Alcance del MVP

La primera versión estará enfocada en productos Kindle.

Fuentes iniciales:

- Woot
- Reddit
- Telegram

Funcionalidades incluidas:

- detectar nuevos productos;
- detectar cupones relacionados con la Watchlist;
- detectar publicaciones relevantes;
- registrar todas las observaciones;
- enviar notificaciones mediante Telegram;
- mantener un historial persistente de observaciones y notificaciones.

---

# 7. Fuera del Alcance del MVP

La primera versión no incluye:

- inteligencia artificial;
- recomendaciones automáticas;
- predicción de precios;
- automatización de compras;
- múltiples usuarios;
- panel web;
- API pública;
- validación automática de cupones;
- análisis avanzados sobre el historial.

---

# 8. Definición de Éxito

El proyecto será considerado exitoso cuando:

- el usuario reciba las notificaciones antes de que las oportunidades desaparezcan;
- el sistema pueda operar de forma continua durante largos periodos con un mantenimiento mínimo;
- todas las observaciones relevantes queden registradas;
- incorporar una nueva fuente únicamente requiera desarrollar un nuevo Collector, sin modificar el núcleo del sistema.

---

# 9. Visión a Largo Plazo

Aunque el MVP estará enfocado inicialmente en Kindle, Sentinel ha sido diseñado para monitorear cualquier producto definido por el usuario.

La arquitectura permitirá incorporar nuevas fuentes de información sin modificar el comportamiento fundamental del sistema.

El objetivo a largo plazo es convertir Sentinel en un observador permanente de oportunidades de compra para cualquier producto incluido en la Watchlist, manteniendo siempre los mismos principios de simplicidad, modularidad y bajo costo operativo.