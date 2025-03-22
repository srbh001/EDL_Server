from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel
import json
from utils.sprint import Logger

l = Logger.get_instance(True)

ws_router = APIRouter()

connections = {}


class Command(BaseModel):
    device_id: str
    phase: str
    command: str


@ws_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # TODO: Add some checks before connection
    l.iprint("Accepting WebSocket connection...")
    await websocket.accept()
    device_id = None
    try:
        data = await websocket.receive_text()
        message = json.loads(data)
        if message.get("type") == "connect" and "device_id" in message:
            device_id = message["device_id"]
            connections[device_id] = websocket
            l.iprint(f"RPi {device_id} connected")
        else:
            await websocket.close(code=1008)

        while True:
            data = await websocket.receive_text()
            l.iprint(f"Received from {device_id}: {data}")
    except WebSocketDisconnect:
        if device_id in connections:
            del connections[device_id]
            l.iprint(f"RPi {device_id} disconnected")


# HTTP endpoint to receive commands from the phone
@ws_router.post("/remote-control")
async def send_command(cmd: Command):
    if cmd.device_id in connections:
        websocket = connections[cmd.device_id]
        # Send command as JSON
        message = {"type": "command", "phase": cmd.phase, "command": cmd.command}
        await websocket.send_text(json.dumps(message))
        return {"status": "command sent"}
    else:
        return {"status": "RPi not connected"}


@ws_router.get("/remote-control/status")
async def get_status(device_id: str = Query(..., description="Device ID of the RPi")):
    l.iprint(f"device_id: {device_id}")

    if device_id in connections:
        websocket = connections[device_id]

        # Send command as JSON
        message = {"type": "command", "command": "status"}
        await websocket.send_text(json.dumps(message))

        try:
            response_text = await websocket.receive_text()
            l.iprint(f"response: {response_text}")
            response = json.loads(response_text)

            # Extracting values safely
            data = {
                "A": response.get("A"),
                "B": response.get("B"),
                "C": response.get("C"),
            }

            return data

        except Exception as e:
            l.eprint(f"Error receiving response: {str(e)}")
            return {"status": "Error processing response"}

    return {"status": "RPi not connected"}
