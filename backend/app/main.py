from fastapi import FastAPI

app = FastAPI(title="Event Companion API")


@app.get("/health")
def health():
    return {"status": "ok"}