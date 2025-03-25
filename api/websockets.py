from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Response, status
from pydantic import BaseModel
import json
from utils.sprint import Logger

l = Logger.get_instance(True)

ws_router = APIRouter()

connections = {}
device_statuses = {}


class Command(BaseModel):
    device_id: str
    phase: str
    command: str


@ws_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    l.iprint("Accepting WebSocket connection...")
    await websocket.accept()
    device_id = None
    try:
        data = await websocket.receive_text()
        message = json.loads(data)
        if message.get("type") == "connect" and "device_id" in message:
            device_id = message["device_id"]
            connections[device_id] = websocket

            if device_id not in device_statuses:
                device_statuses[device_id] = {
                    "A": None,
                    "B": None,
                    "C": None,
                }
            l.iprint(f"RPi {device_id} connected")
        else:
            await websocket.close(code=1008)

        while True:
            data = await websocket.receive_text()
            l.iprint(f"Received from {device_id}: {data}")
            message = json.loads(data)

            if "status" in message:
                device_statuses[device_id] = {
                    "A": message["status"].get("A"),
                    "B": message["status"].get("B"),
                    "C": message["status"].get("C"),
                }
                l.iprint(
                    f"Updated status for {device_id}: {device_statuses[device_id]}"
                )
    except WebSocketDisconnect:
        if device_id in connections:
            del connections[device_id]
            l.iprint(f"RPi {device_id} disconnected")


# HTTP endpoint to receive commands from the phone
@ws_router.post("/remote-control")
async def send_command(cmd: dict):
    l.iprint("COMMAND: ", cmd)
    if cmd["device_id"] in connections:
        websocket = connections[cmd["device_id"]]
        # Send command as JSON
        message = {"type": "command", "phase": cmd["phase"], "command": cmd["command"]}
        await websocket.send_text(json.dumps(message))
        msg = json.dumps({"status": "command sent"})
        return Response(content=msg, status_code=200)
    else:
        return Response(
            content=json.dumps({"status": "RPi not connected"}), status_code=404
        )


@ws_router.get("/remote-control/status")
async def get_status(device_id: str = Query(..., description="Device ID of the RPi")):
    """Returns the status of the RPi"""

    l.iprint(f"device_id: {device_id}")

    if device_id not in connections:
        return Response(
            content=json.dumps({"status": "RPi not connected"}), status_code=404
        )

    if device_id in device_statuses:
        l.iprint("Status already available")
        websocket = connections[device_id]

        status = device_statuses[device_id]

        data = {
            "A": None,
            "B": None,
            "C": None,
        }

        if status:
            data = {
                "A": status.get("A"),
                "B": status.get("B"),
                "C": status.get("C"),
            }

        # Send command as JSON
        message = {"type": "command", "command": "status"}
        await websocket.send_text(json.dumps(message))
        l.iprint("Sent status request to RPi")
        # return Response(content=json.dumps(data), status_code=200)
        return Response(json.dumps(data), status_code=200)

    return Response(
        content=json.dumps({"status": "Rpi not connected"}), status_code=404
    )
