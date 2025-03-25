import asyncio
import websockets
import json
import random


async def websocket_client():
    uri = "wss://edlserver-production.up.railway.app/ws"  # Change this if needed
    device_id = "random12"

    async with websockets.connect(uri) as websocket:
        # Send initial connection message
        connect_msg = json.dumps({"type": "connect", "device_id": device_id})
        await websocket.send(connect_msg)

        print("Connected to server")
        response = await websocket.recv()
        print(f"Server response: {response}")

        async def send_status_updates():
            """Send periodic status updates."""
            while True:
                await asyncio.sleep(5)  # Send status every 5 seconds
                status_msg = {
                    "A": random.choice(["on", "off"]),
                    "B": random.choice(["on", "off"]),
                    "C": random.choice(["on", "off"]),
                }
                await websocket.send(json.dumps(status_msg))
                print(f"Sent status: {status_msg}")

        asyncio.create_task(
            send_status_updates()
        )  # Run status updates in the background

        while True:
            try:
                response = await websocket.recv()
                print(f"Server response: {response}")
                message = json.loads(response)

                if message.get("type") == "command":
                    phase = message.get("phase")
                    command = message.get("command")

                    if phase and command:
                        print(f"Received command for Phase {phase}: {command.upper()}")
                        # Just acknowledge the command
                        ack_msg = {
                            "type": "response",
                            "phase": phase,
                            "status": "executed",
                            "command": command,
                        }
                        await websocket.send(json.dumps(ack_msg))
                        print(f"Sent acknowledgment: {ack_msg}")

            except websockets.exceptions.ConnectionClosed:
                print("Server disconnected")
                break
            except KeyboardInterrupt:
                print("Disconnected by user")
                break
            except Exception as e:
                print(f"Error: {e}")
                break


if __name__ == "__main__":
    asyncio.run(websocket_client())
