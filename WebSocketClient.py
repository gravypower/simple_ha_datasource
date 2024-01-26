import asyncio
import logging
import websockets
import json
import threading

class WebSocketClient:
    def __init__(self, uri, token):
        self.uri = uri
        self.token = token
        self.websocket = None
        self.lock = asyncio.Lock()  # Lock for send method
        self.request_id = 0
        self.request_id_lock = asyncio.Lock()  # Lock for request ID generation


    def start(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.connect())
        loop.run_forever()

    async def connect(self):
        self.websocket = await websockets.connect(self.uri)
        await self.authenticate()

    async def authenticate(self):
        auth_message = {
            "type": "auth",
            "access_token": self.token
        }
        await self.websocket.send(json.dumps(auth_message))
        auth_response = await self.websocket.recv()
        logging.info(f"Auth response: {auth_response}")
        auth_response = json.loads(auth_response)

        if auth_response['type'] == 'auth_invalid':
            raise Exception("Authentication failed with Home Assistant")

    async def send(self, message):
        if self.websocket is None or self.websocket.closed:
            await self.connect()  # Reconnect if the connection is closed
        try:
            await self.websocket.send(json.dumps(message))
            response = await self.websocket.recv()
            if response is None:
                raise ValueError("Received None response from WebSocket server")
            return response
        except websockets.exceptions.ConnectionClosed as e:
            logging.error(f"WebSocket connection closed unexpectedly: {e}")
            await self.connect()
            # Optionally retry sending the message or handle the error


    async def get_next_request_id(self):
        async with self.request_id_lock:
            self.request_id += 1
            return self.request_id
    
    async def fetch_statistics(self, statistic_id, start_time, end_time):
        request_id = await self.get_next_request_id()
        stats_request = {
            "type": "recorder/statistics_during_period",
            "start_time": start_time,
            "end_time": end_time,
            "statistic_ids": [statistic_id],
            "period": "hour",
            "types": ["mean", "state"],
            "id": request_id
        }
        logging.info(f"sending: {json.dumps(stats_request, indent=4)}")
        response = await self.send(stats_request)
        if response is None:
            logging.error("Received None response in fetch_statistics")
            return None  # Or handle this case as needed
        parsed_response = json.loads(response)
        logging.info(f"WebSocket API response: {parsed_response}")
        return parsed_response