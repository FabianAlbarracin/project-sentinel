# Project Sentinel

Observador permanente de oportunidades de compra. Monitorea fuentes de internet,
detecta coincidencias con la Watchlist del usuario y notifica por Telegram.

## Arranque

```bash
cp .env.example .env
# Editar .env con credenciales reales
docker compose up -d
```

## Verificar

```bash
docker logs project_sentinel
```

## Documentacion

La fuente de verdad arquitectonica esta en `docs/`. Leer antes de modificar codigo.
