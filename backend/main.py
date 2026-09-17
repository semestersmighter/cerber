from fastapi import Depends,FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth import router as auth_router
from auth_dependencies import get_current_user

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # à restreindre en prod (ex: http://localhost:8080)
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

@app.get("/api/hello")
def hello():
    return {"message": "Hello depuis FastAPI"}

@app.get("/api/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return current_user
