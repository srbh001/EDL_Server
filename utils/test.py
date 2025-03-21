import asyncio
import websockets
import json


async def websocket_client():
    uri = "wss://edlserver-production.up.railway.app/ws"  # Change this if your server runs elsewhere
    async with websockets.connect(uri) as websocket:
        # Send initial connection message
        connect_msg = json.dumps({"type": "connect", "device_id": "random12"})
        await websocket.send(connect_msg)

        print("Connected to server")
        response = await websocket.recv()  # Print server's first response
        print(f"Server response: {response}")

        while True:
            try:
                response = await websocket.recv()
                print(f"Server response: {response}")

            except KeyboardInterrupt:
                print("Disconnected by user")
                break
            except Exception as e:
                print(f"Error: {e}")
                break


if __name__ == "__main__":
    asyncio.run(websocket_client())
