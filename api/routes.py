from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from influxdb_client import Point, WritePrecision
from datetime import datetime, timedelta
from utils.database import write_api, query_api
from utils.security import verify_token
from config import settings

router = APIRouter()
BUCKET = settings.influxdb_bucket
ORG = settings.influxdb_org


@router.post("/write-data")
async def write_data(
    power_data: list[dict] = None,
    energy_data: list[dict] = None,
    payload: str = Depends(verify_token),
):
    """Batch write power and energy data to InfluxDB."""
    device_id = payload.get("device_id")
    points = []
    time_now = datetime.utcnow()

    if power_data:
        for p in power_data:
            try:
                timestamp = datetime.strptime(p["time"], "%Y-%m-%dT%H:%M:%S.%fZ")
            except (KeyError, ValueError, TypeError):
                timestamp = (
                    time_now  # Use current time if key is missing or invalid format
                )

            points.append(
                Point("power_data")
                .tag("device_id", device_id)
                .tag("phase", p["phase"])
                .field("power_watt", p["power_watt"])
                .field("power_var", p["power_var"])
                .field("power_va", p["power_va"])
                .field("voltage_rms", p["voltage_rms"])
                .field("current_rms", p["current_rms"])
                .field("power_factor", p["power_factor"])
                .field("voltage_thd", p["voltage_thd"])
                .field("current_thd", p["current_thd"])
                .field("energy_kwh", p["energy_kwh"])
                .time(timestamp, WritePrecision.NS)
            )

    if not points:
        raise HTTPException(status_code=400, detail="No valid data to write.")

    write_api.write(bucket=BUCKET, org=ORG, record=points)

    return JSONResponse(
        content={"message": "Data written successfully."}, status_code=201
    )


@router.get("/query-data/")
async def query_data(range_hours: int = 240, device_id: str = "random12"):
    """Query power and energy data for a specific device, grouped by phase."""
    time_range = f"-{range_hours}h"

    # Flux Query
    query = f"""
    from(bucket: "{BUCKET}")
      |> range(start: {time_range})
      |> filter(fn: (r) => r.device_id == "{device_id}")
      |> group(columns: ["phase"])  // Group by phase
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")  // Pivot for structured output
      |> keep(columns: ["_time", "phase", "power_watt", "voltage_rms", "current_rms", "energy_kwh"])  // Keep only relevant fields
    """

    tables = query_api.query(query, org=ORG)
    formatted_results = {}

    for table in tables:
        for record in table.records:
            timestamp = record.get_time().isoformat()
            phase = record.values.get("phase", "Unknown")
            if phase not in formatted_results:
                formatted_results[phase] = []

            formatted_results[phase].append(
                {
                    "timestamp": timestamp,
                    "power_watt": record.values.get("power_watt", None),
                    "voltage_rms": record.values.get("voltage_rms", None),
                    "current_rms": record.values.get("current_rms", None),
                    "energy_kwh": record.values.get("energy_kwh", None),
                }
            )

    return JSONResponse(content=formatted_results, status_code=200)


@router.get("/fetch-analytics/")
async def fetch_analytics(device_id: str):
    """Fetch analytics data for a given device."""
    query = f"""
    from(bucket: "{BUCKET}")
      |> range(start: -30d)
      |> filter(fn: (r) => r._measurement == "analytics_data")
      |> filter(fn: (r) => r.device_id == "{device_id}")
    """
    tables = query_api.query(query, org=ORG)
    analytics_results = {}

    for table in tables:
        for record in table.records:
            field = record.get_field()
            value = record.get_value()
            analytics_results[field] = value

    return JSONResponse(content=analytics_results, status_code=200)


@router.get("/fetch-all")
async def fetch_all_data():
    """Fetch all data in the InfluxDB bucket without authentication for testing"""

    query = f"""
    from(bucket: "{BUCKET}")
      |> range(start: -30d)  // Fetch last 30 days of data
    """

    tables = query_api.query(query, org=ORG)

    results = []

    for table in tables:
        for record in table.records:
            results.append(
                {
                    "measurement": record.get_measurement(),
                    "device_id": record.values.get("device_id"),
                    "field": record.values.get("_field"),
                    "value": record.get_value(),
                    "time": record.get_time(),
                }
            )

    return {"data": results}


@router.get("/latest-values")
async def get_latest_values():
    """Get the latest values of voltage, current, and power for each phase (A, B, C) of the device."""
    device_id = "random12"
    query = f'''
    
    from(bucket: "{BUCKET}")
    |> range(start: -1h)  // Consider last 1 hour
    |> filter(fn: (r) => r._measurement == "power_data")
    |> filter(fn: (r) => r.device_id == "{device_id}")
    |> filter(fn: (r) => r._field == "voltage_rms" or r._field == "current_rms" or r._field == "power_watt")
    |> group(columns: ["_field", "phase"])  // Ensure phase and field are properly grouped
    |> last()  // Get the latest value per field and phase
    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''
    tables = query_api.query(query, org=ORG)
    latest_values = {}

    for table in tables:
        for record in table.records:
            print("[DEBUG] Record: ", record.values)
            phase = record.values.get("phase")
            if not phase:
                continue  # Skip if phase is missing
            latest_values[phase] = {
                "timestamp": record.values.get("_time").isoformat(),
                "voltage": record.values.get("voltage_rms"),
                "current": record.values.get("current_rms"),
                "power": record.values.get("power_watt"),
            }

    if not latest_values:
        return JSONResponse(
            content={"message": "No data found for the device."}, status_code=404
        )

    return JSONResponse(content=latest_values, status_code=200)


@router.get("/thd-values")
async def get_thd_data():
    """Get the thd values of all three phases"""

    device_id = "random12"
    query = f'''

    from(bucket: "{BUCKET}")
      |> range(start: -1y)
      |> filter(fn: (r) => r.device_id == "{device_id}")
      |> filter(fn: (r) => r._measurement == "power_data")
      |> group(columns: ["phase"])  // Group by phase
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")  // Pivot for structured output
      |> keep(columns: ["_time", "phase", "power_factor", "voltage_thd", "current_thd"])  // Keep only relevant fields
    '''

    tables = query_api.query(query, org=ORG)

    latest_values = {}

    for table in tables:
        for record in table.records:
            print("[DEBUG] Record: ", record.values)
            phase = record.values.get("phase")
            if not phase:
                continue  # Skip if phase is missing

            data_point = {
                "timestamp": record.values.get("_time").isoformat(),
                "voltage_thd": record.values.get("voltage_thd"),
                "current_thd": record.values.get("current_thd"),
                "power_factor": record.values.get("power_factor"),
            }
            if phase not in latest_values:
                latest_values[phase] = [data_point]
            else:
                latest_values[phase].append(data_point)

    if not latest_values:
        return JSONResponse(
            content={"message": "No data found for the device."}, status_code=404
        )

    return JSONResponse(content=latest_values, status_code=200)
