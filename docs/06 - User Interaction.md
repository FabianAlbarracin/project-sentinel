# 06 - User Interaction.md

# Project Sentinel
## User Interaction

**Versión:** 1.0

---

# 1. Objetivo

Este documento define la interacción entre Project Sentinel y el usuario durante el MVP.

En esta primera versión Sentinel actuará únicamente como un sistema de notificaciones.

La comunicación será unidireccional.

El usuario no enviará comandos al sistema ni existirá interacción conversacional.

---

# 2. Principios

## 2.1 Rapidez

Una notificación debe poder comprenderse en pocos segundos.

El usuario debe decidir rápidamente si desea abrir la publicación original.

---

## 2.2 La fuente siempre tiene prioridad

Sentinel no intenta reemplazar la publicación original.

Su objetivo consiste únicamente en informar que apareció una nueva oportunidad.

Toda la información detallada permanece en la fuente.

---

## 2.3 Información útil

Cada notificación mostrará únicamente los datos necesarios para tomar una decisión.

No intentará mostrar información técnica innecesaria.

---

## 2.4 Consistencia

Cada tipo de Observation tendrá siempre el mismo formato.

El usuario deberá reconocer inmediatamente el tipo de notificación recibida.

---

# 3. Canal de Comunicación

Durante el MVP existirá un único canal.

```
Telegram Bot
```

No existirán:

- comandos
- menús
- botones interactivos
- consultas
- respuestas automáticas

Telegram funcionará únicamente como canal de salida.

---

# 4. Tipos de Notificación

Sentinel podrá enviar tres tipos de mensajes.

---

## Producto detectado

Corresponde a una publicación realizada por una tienda.

Ejemplos

- Woot

---

## Cupón detectado

Corresponde a un código de descuento relacionado con un producto de la Watchlist.

Puede provenir de cualquier Source.

Ejemplos

- Woot
- Reddit
- Telegram

---

## Publicación relevante

Corresponde a una publicación relacionada con un Watch Item.

Ejemplos

- Reddit
- Telegram

---

# 5. Formato de las Notificaciones

## 5.1 Producto

```text
📦 Producto detectado

Fuente:
Woot

Producto:
Amazon Kindle Paperwhite

Precio:
89.99 USD

Estado:
Certified Refurbished

Modelos:
• 8 GB
• 16 GB Signature Edition

Colores:
• Black
• Denim

──────────────

🔗 Abrir publicación
```

### Reglas

- Si la fuente no proporciona un dato, simplemente no se mostrará.
- Sentinel nunca inventa información.
- El orden de los campos siempre será el mismo.

---

## 5.2 Cupón

```text
🎟 Cupón detectado

Código:
KINDLE25

Fuente:
Reddit

Título:
Woot with Kindles on sale

──────────────

🔗 Abrir publicación
```

### Reglas

Sentinel únicamente informa que una fuente publicó un cupón.

No verifica si funciona.

---

## 5.3 Publicación

```text
💬 Publicación relevante

Fuente:
Reddit

Título:
Woot with Kindles on sale

──────────────

🔗 Abrir publicación
```

No se resumirá el contenido.

El usuario leerá la publicación directamente desde la fuente.

---

## 5.4 Mensaje de Telegram

```text
📢 Mensaje relevante

Grupo:
Kindle Deals

──────────────

(mensaje original)

──────────────
```

El contenido del mensaje será reenviado prácticamente sin modificaciones.

Los enlaces originales deberán conservarse.

---

# 6. Información que Sentinel intentará extraer

Dependiendo de la información disponible en la fuente.

## Producto

Nombre del artículo.

---

## Precio

Precio publicado.

Si la fuente proporciona varias variantes, Sentinel decidirá posteriormente cómo representarlas.

El modelo de datos no asumirá una estructura hasta conocer el formato real de la fuente.

---

## Estado

Ejemplos

- New
- Certified Refurbished
- Used
- Open Box

---

## Modelos

Ejemplos

- 8 GB
- 16 GB Signature Edition

---

## Colores

Cuando la publicación los incluya.

---

## Cupón

Código de descuento.

---

## Enlace

Siempre existirá un enlace hacia la publicación original.

---

# 7. Información que NO mostrará

Sentinel no intentará mostrar:

- especificaciones técnicas;
- descripción comercial;
- opiniones;
- reseñas;
- información de envío;
- disponibilidad por región;
- datos internos de la tienda.

Toda esa información pertenece a la publicación original.

---

# 8. Emojis

Los emojis únicamente identifican el tipo de Observation.

| Emoji | Significado |
|--------|-------------|
| 📦 | Producto |
| 🎟 | Cupón |
| 💬 | Publicación |
| 📢 | Mensaje de Telegram |

No se utilizarán emojis decorativos adicionales.

---

# 9. Duplicados

Cada Observation podrá generar como máximo una Notification.

Si la misma Observation vuelve a detectarse posteriormente, no deberá notificarse nuevamente.

Si diferentes Sources publican información similar, cada Observation se tratará de forma independiente.

Ejemplo

- Woot publica un Kindle.
- Reddit publica el enlace.
- Telegram comparte la misma oferta.

Cada publicación constituye una Observation distinta y podrá generar su propia Notification.

---

# 10. Errores

Si una Notification no puede enviarse:

- la Observation permanecerá almacenada;
- el error quedará registrado;
- el fallo de Telegram nunca afectará la ejecución de los Collectors.

---

# 11. Evolución

En futuras versiones podrán incorporarse:

- comandos mediante Telegram;
- consultas sobre el historial;
- filtros personalizados;
- múltiples usuarios;
- nuevos canales de notificación.

Estas funcionalidades no forman parte del MVP.

---

# 12. Principio de Diseño

Project Sentinel no pretende reemplazar las fuentes originales.

Su responsabilidad consiste en avisar al usuario, con la menor latencia posible, que apareció una nueva oportunidad relacionada con un elemento de su Watchlist.

La decisión de abrir la publicación, utilizar un cupón o realizar una compra corresponde siempre al usuario.