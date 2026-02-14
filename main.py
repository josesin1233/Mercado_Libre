from fastapi import FastAPI

app = FastAPI(title="Mercado Libre App")


@app.get("/")
def root():
    return {"status": "ok", "message": "Mercado Libre App corriendo"}
