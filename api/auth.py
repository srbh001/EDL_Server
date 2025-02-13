from fastapi import APIRouter, Depends, HTTPException
from influxdb_client import Point
from datetime import datetime
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import JSONResponse

from utils.database import write_api, query_api
from utils.security import create_access_token
from config import settings


security = HTTPBasic()

router = APIRouter()

BUCKET = settings.influxdb_bucket
ORG = settings.influxdb_org


@router.post("/login")
async def login(credentials: HTTPBasicCredentials = Depends(security)):
    """Login and authenticate user against InfluxDB using Basic Auth"""

    query = f"""
    from(bucket: "{BUCKET}")
      |> range(start: -30d)
      |> filter(fn: (r) => r._measurement == "user_auth")
    """
    tables = query_api.query(query, org=ORG)

    latest_records = {}  # Store latest uname-password-device_id triplets

    # Iterate over all records to find username and password
    for table in tables:
        for record in table.records:
            device_id = record.values.get("device_id")
            record_time = record.get_time()
            field = record.values.get("_field")
            value = record.values.get("_value")

            if device_id not in latest_records:
                latest_records[device_id] = {
                    "uname": None,
                    "password": None,
                    "timestamp": None,
                }

            if (
                latest_records[device_id]["timestamp"] is None
                or record_time > latest_records[device_id]["timestamp"]
            ):
                latest_records[device_id]["timestamp"] = record_time

            if field == "uname":
                latest_records[device_id]["uname"] = value
            elif field == "password":
                latest_records[device_id]["password"] = value

    matched_device_id = None
    stored_password = None

    for device_id, user_data in latest_records.items():
        if user_data["uname"] == credentials.username:
            matched_device_id = device_id
            stored_password = user_data["password"]
            break

    if not matched_device_id or credentials.password != stored_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(
        device_id=matched_device_id, username=credentials.username
    )

    return JSONResponse(
        content={"access_token": access_token, "token_type": "bearer"}, status_code=200
    )


@router.post("/sign-up")
async def sign_up(username: str, password: str, device_code: str):
    """Initial sign-up of the phone application with the server.

    - Retrieves all `device_keys` records.
    - Verifies if `device_code` exists in any of the records.
    - Stores `username` and `hashed password` in `user_auth`.
    - Returns an authentication token.
    """

    # Query all device_keys records
    query = f"""
    from(bucket: "{BUCKET}")
      |> range(start: -30d)
      |> filter(fn: (r) => r._measurement == "device_keys")
    """
    tables = query_api.query(query, org=ORG)

    print("[INFO]: Retrieved device_keys tables:", tables)

    device_id = None

    # Check for matching device_code
    for table in tables:
        for record in table.records:
            if record.get_value() == device_code:  # Checking device_code here
                device_id = record.values.get("device_id")
                break

    if not device_id:
        raise HTTPException(status_code=400, detail="Invalid device code")

    hashed_password = password  # FIXME: Replace with actual hashing

    point = (
        Point("user_auth")
        .tag("device_id", device_id)
        .field("uname", username)
        .field("password", hashed_password)  # Store only the hashed password
        .time(datetime.utcnow())
    )
    write_api.write(bucket=BUCKET, org=ORG, record=point)

    # Generate authentication token
    token = create_access_token(device_id=device_id, username=username)

    return JSONResponse(
        content={"message": "User created successfully", "access_token": token},
        status_code=201,
    )
