from fastapi import FastAPI
import uvicorn

app = FastAPI(title="server")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello from FastAPI"}


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
