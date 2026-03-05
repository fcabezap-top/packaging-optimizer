from fastapi import FastAPI

app = FastAPI(title="Users Service")

@app.get("/")
def health():
    return {"service": "users", "status": "ok"}
