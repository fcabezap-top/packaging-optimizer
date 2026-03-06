from fastapi import FastAPI
from .routers import products, families, subfamilies, campaigns

app = FastAPI(title="Product Service")

app.include_router(families.router)
app.include_router(subfamilies.router)
app.include_router(campaigns.router)
app.include_router(products.router)


@app.get("/")
def health():
    return {"service": "product", "status": "ok"}

