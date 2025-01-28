from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from influxdb_client import InfluxDBClient
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

from base.routes import base_router

# Load environment variables from .env file
load_dotenv()


# Define settings using Pydantic's BaseSettings
class Settings(BaseSettings):
    influxdb_url: str = os.getenv("INFLUXDB_URL")
    influxdb_token: str = os.getenv("INFLUXDB_TOKEN")
    influxdb_org: str = os.getenv("INFLUXDB_ORG")
    influxdb_bucket: str = os.getenv("INFLUXDB_BUCKET")


settings = Settings()


influxdb_client = InfluxDBClient(
    url=settings.influxdb_url, token=settings.influxdb_token, org=settings.influxdb_org
)

# Security scheme for Bearer token
security = HTTPBearer()


# Dependency to verify the token
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Here you can add additional logic to verify the token if needed
    # For simplicity, we assume the token is valid if it matches the InfluxDB token
    if credentials.credentials != settings.influxdb_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


app = FastAPI()


@app.get("/query-data/")
async def query_data():
    query_api = influxdb_client.query_api()
    query = f"""
    from(bucket: "{settings.influxdb_bucket}")
      |> range(start: -1h)
      |> filter(fn: (r) => r._measurement == "my_measurement")
    """
    result = query_api.query(query)
    return {"data": result.to_json()}


app.include_router(base_router, prefix="/base")
