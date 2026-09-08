from fastapi import FastAPI

app = FastAPI(title="TaskFlow API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
