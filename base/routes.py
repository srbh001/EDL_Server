from fastapi import APIRouter

base_router = APIRouter()


@base_router.get("/")
def index():
    """Return Hello World message"""
    return {"message": "Hello World"}


@base_router.get("/data")
def get_data():
    """Return some data"""
    return {"data": "some data"}
