from fastapi import FastAPI
from api.routes import router as api_router
from api.auth import router as auth_router

app = FastAPI()

app.include_router(api_router, prefix="/api")
app.include_router(auth_router, prefix="/auth")
