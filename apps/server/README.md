# Server

Proyecto base de FastAPI gestionado con `uv`.

## Ejecutar

```bash
uv run python main.py
```

La API queda disponible en `http://127.0.0.1:8000`.

## Endpoints

- `GET /`
- `GET /health`

## Alternativa

```bash
uv run uvicorn main:app --reload
```
