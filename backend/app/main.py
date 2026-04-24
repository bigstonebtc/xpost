from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth, tweets, queue, history

Base.metadata.create_all(bind=engine)

app = FastAPI(title="xpost API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tweets.router)
app.include_router(queue.router)
app.include_router(history.router)


@app.get("/health")
def health():
    return {"status": "ok"}
