from fastapi import FastAPI

app = FastAPI(title="Medical RAG API")

@app.get("/")
def read_root():
    return {"status": "ok"}
