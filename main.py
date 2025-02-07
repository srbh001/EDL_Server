from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from influxdb_client import InfluxDBClient, Point
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import datetime
import os

from base.routes import base_router

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    influxdb_url: str = os.getenv("INFLUXDB_URL")
    influxdb_token: str = os.getenv("INFLUXDB_TOKEN")
    influxdb_org: str = os.getenv("INFLUXDB_ORG")
    influxdb_bucket: str = os.getenv("INFLUXDB_BUCKET")


settings = Settings()

BUCKET = settings.influxdb_bucket
ORG = settings.influxdb_org


influxdb_client = InfluxDBClient(
    url=settings.influxdb_url, token=settings.influxdb_token, org=settings.influxdb_org
)
write_api = influxdb_client.write_api()
query_api = influxdb_client.query_api()

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


@app.post("/write_data/")
async def write_data(I: float, V: float, P: float, device_id: str):

    point = (
        Point("sensor_data")
        .tag("device_id", device_id)
        .field("I", I)
        .field("V", V)
        .field("P", P)
        .time(datetime.datetime.utcnow())
    )  # Automatically adds timestamp

    write_api.write(bucket=BUCKET, org=ORG, record=point)
    return {"message": "Data written successfully"}


@app.get("/query-data/")
async def query_data():
    query = f"""
    from(bucket: "{BUCKET}")
      |> range(start: -24h)
      |> filter(fn: (r) => r._measurement == "sensor_data")
    """
    tables = query_api.query(query, org=ORG)

    formatted_results = {}

    for table in tables:
        for record in table.records:
            device_id = record.values.get("device_id", "unknown")
            timestamp = record.get_time().isoformat()
            field = record.get_field()
            value = record.get_value()

            if device_id not in formatted_results:
                formatted_results[device_id] = {}

            if timestamp not in formatted_results[device_id]:
                formatted_results[device_id][timestamp] = {}

            formatted_results[device_id][timestamp][field] = value

    return {"data": formatted_results}


app.include_router(base_router, prefix="/base")
