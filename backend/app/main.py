from fastapi import FastAPI

app = FastAPI(title="German Scene-Based SRS API")

@app.get("/health")
def health_check():
    return {"status": "ok"}