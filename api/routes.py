from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from influxdb_client import Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime, timedelta
import random

from utils.database import write_api, query_api
from utils.security import verify_token
from config import settings

router = APIRouter()

BUCKET = settings.influxdb_bucket
ORG = settings.influxdb_org


@router.post("/generate-data/")
async def generate_data(num_points: int = Query(100, ge=1, le=1000)):
    """
    Generates `num_points` of random sensor data and writes to InfluxDB.
    """
    # TODO: Generate data in more useful patterns.
    time_now = datetime.utcnow()
    time_start = time_now - timedelta(hours=24)  # Data spread over the last 24 hours

    for _ in range(num_points):
        timestamp = time_start + timedelta(
            seconds=random.randint(0, 86400)
        )  # Random time
        I = round(random.uniform(0.1, 10.0), 2)  # Random Current (I)
        V = round(random.uniform(110.0, 250.0), 2)  # Random Voltage (V)
        P = round(I * V, 2)  # Power (P = I * V)

        # Create and write InfluxDB point
        point = (
            Point("sensor_data")
            .tag("device_id", "random12")
            .field("I", I)
            .field("V", V)
            .field("P", P)
            .time(timestamp, WritePrecision.NS)
        )
        write_api.write(bucket=BUCKET, org=ORG, record=point)

    return JSONResponse(
        content={"message": f"{num_points} data points written successfully."},
        status_code=201,
    )


@router.post("/write-data/")
async def write_data(
    I: float, V: float, P: float, payload: str = Depends(verify_token)
):
    """Write sensor data to InfluxDB with device_id as a tag."""
    device_id = payload.get("device_id")
    point = (
        Point("sensor_data")
        .tag("device_id", device_id)
        .field("I", I)
        .field("V", V)
        .field("P", P)
        .time(datetime.utcnow())
    )
    write_api.write(bucket=BUCKET, org=ORG, record=point)

    return JSONResponse(
        content={"message": "Data written successfully."}, status_code=201
    )


@router.get("/query-data/")
async def query_data(device_id: str):
    """Query sensor data from InfluxDB for a specific device (last 24h)."""
    query = f"""
    from(bucket: "{BUCKET}")
      |> range(start: -24h)
      |> filter(fn: (r) => r._measurement == "sensor_data")
      |> filter(fn: (r) => r.device_id == "{device_id}")
    """
    tables = query_api.query(query, org=ORG)

    formatted_results = {}
    for table in tables:
        for record in table.records:
            timestamp = record.get_time().isoformat()
            field = record.get_field()
            value = record.get_value()

            if timestamp not in formatted_results:
                formatted_results[timestamp] = {}

            formatted_results[timestamp][field] = value

    return JSONResponse(content=formatted_results, status_code=200)


@router.get("/get-data")
async def get_data(device_id: str, range: int):
    """Query I, V, P data for a given range of time and device_id."""
    time_range = f"-{range}h"
    query = f"""
    from(bucket: "{BUCKET}")
      |> range(start: {time_range})
      |> filter(fn: (r) => r._measurement == "sensor_data")
      |> filter(fn: (r) => r.device_id == "{device_id}")
    """

    tables = query_api.query(query, org=ORG)
    formatted_results = {}

    for table in tables:
        for record in table.records:
            timestamp = record.get_time().isoformat()
            field = record.get_field()
            value = record.get_value()

            if timestamp not in formatted_results:
                formatted_results[timestamp] = {}

            formatted_results[timestamp][field] = value

    return JSONResponse(content=formatted_results, status_code=200)


@router.get("/fetch-all")
async def fetch_all_data():
    """Fetch all data from user_auth, device_keys, and sensor_data."""

    datasets = {"user_auth": {}, "device_keys": {}, "sensor_data": {}}

    measurements = ["user_auth", "device_keys", "sensor_data"]

    for measurement in measurements:
        query = f"""
        from(bucket: "{BUCKET}")
          |> range(start: -30d)  
          |> filter(fn: (r) => r._measurement == "{measurement}")
        """
        tables = query_api.query(query, org=ORG)

        for table in tables:
            for record in table.records:
                device_id = record.values.get(
                    "device_id", "unknown"
                )  # Extract device_id
                timestamp = record.get_time().isoformat()
                field = record.get_field()
                value = record.get_value()

                if device_id not in datasets[measurement]:
                    datasets[measurement][device_id] = {}

                if timestamp not in datasets[measurement][device_id]:
                    datasets[measurement][device_id][timestamp] = {}

                datasets[measurement][device_id][timestamp][field] = value

    return JSONResponse(content=datasets, status_code=200)
