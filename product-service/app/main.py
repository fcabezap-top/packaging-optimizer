from fastapi import FastAPI

app = FastAPI(title="Product Service")

@app.get("/")
def health():
    return {"service": "product", "status": "ok"}
