# Infra Scripts

Scripts operativos para observar y ejecutar la pipeline de evaluacion de catalogo.

## Requisitos

- Docker Desktop levantado
- contenedores del proyecto disponibles via `docker compose`
- ejecutar desde la raiz del repo

## Scripts disponibles

### `monitor_catalog.ps1`

Imprime un dashboard de estado del catalogo y de los benchmark runs.

Incluye:

- conteo por `evaluation_status`
- modelos `verified` que ya compiten en routing
- modelos `provisional` pendientes de live
- modelos `rejected`
- ultimos runs `live`
- ultimos runs `heuristic`
- fallos recientes de `live`
- safety check para asegurar que solo `verified` entra a routing

Uso:

```powershell
powershell -ExecutionPolicy Bypass -File "scripts/monitor_catalog.ps1"
```

### `run_catalog_eval.ps1`

Lanza la pipeline manual de evaluacion de catalogo dentro del contenedor `backend`.

Uso basico:

```powershell
powershell -ExecutionPolicy Bypass -File "scripts/run_catalog_eval.ps1"
```

## Ejemplos utiles

### 1. Ver dashboard completo

```powershell
powershell -ExecutionPolicy Bypass -File "scripts/monitor_catalog.ps1"
```

### 2. Correr una pasada pequena para prueba

```powershell
powershell -ExecutionPolicy Bypass -File "scripts/run_catalog_eval.ps1" -MaxModels 5 -MaxLive 2
```

### 3. Correr solo heuristico

```powershell
powershell -ExecutionPolicy Bypass -File "scripts/run_catalog_eval.ps1" -MaxModels 20 -MaxLive 0
```

### 4. Correr solo live sobre provisionales

```powershell
powershell -ExecutionPolicy Bypass -File "scripts/run_catalog_eval.ps1" -MaxModels 0 -MaxLive 10
```

### 5. Limitar a ciertos providers

```powershell
powershell -ExecutionPolicy Bypass -File "scripts/run_catalog_eval.ps1" -ProviderAllowlist "openai,anthropic"
```

### 6. Re-evaluar tambien modelos ya verificados

```powershell
powershell -ExecutionPolicy Bypass -File "scripts/run_catalog_eval.ps1" -IncludeVerifiedLive
```

## Notas

- `run_catalog_eval.ps1` usa por defecto el servicio `backend` de `docker compose`.
- `monitor_catalog.ps1` usa por defecto el contenedor `llm-router-db`.
- Si cambias nombres de servicios o contenedores, puedes ajustar los parametros del script.
- La automatizacion tras sync depende de `CATALOG_EVALUATION_AFTER_OPENROUTER_SYNC=true` en `.env` y de recrear el contenedor `backend` si cambias variables de entorno.
