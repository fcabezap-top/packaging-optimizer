from fastapi import FastAPI

app = FastAPI(title="Optimization Service")

@app.get("/")
def health():
    return {"service": "optimization", "status": "ok"}
