import asyncio
import json
import logging
import websockets

class WebSocketClient:
    def __init__(self, uri, token):
        self.uri = uri
        self.token = token
        self.websocket = None
        self.lock = asyncio.Lock()
        self.request_id_lock = asyncio.Lock()
        self.request_id = 0
        self.authenticated = False
        self.pending_responses = {}

    async def connect(self):
        self.websocket = await websockets.connect(self.uri)
        await self.authenticate()
        asyncio.create_task(self.listen_for_responses())

    async def authenticate(self):
        auth_message = {"type": "auth", "access_token": self.token}
        await self.websocket.send(json.dumps(auth_message))
        response = await self.websocket.recv()
        response_data = json.loads(response)
        if response_data['type'] == 'auth_ok':
            self.authenticated = True
        elif response_data['type'] == 'auth_invalid':
            raise Exception("Authentication failed with Home Assistant")

    async def send(self, message):
        async with self.lock:
            request_id = await self.get_next_request_id()
            message['id'] = request_id
            self.pending_responses[request_id] = asyncio.Future()
            await self.websocket.send(json.dumps(message))
            return await self.wait_for_response(request_id)

    async def get_next_request_id(self):
        async with self.request_id_lock:
            self.request_id += 1
            return self.request_id

    async def wait_for_response(self, request_id):
        future = self.pending_responses[request_id]
        await future
        response = future.result()
        del self.pending_responses[request_id]
        return response

    async def listen_for_responses(self):
        while True:
            response = await self.websocket.recv()
            response_data = json.loads(response)
            request_id = response_data.get('id')
            if request_id in self.pending_responses:
                self.pending_responses[request_id].set_result(response_data)

    async def fetch_statistics(self, entity_ids, start_time, end_time):
        stats_request = {
            "type": "recorder/statistics_during_period",
            "start_time": start_time,
            "end_time": end_time,
            "statistic_ids": entity_ids,
            "period": "hour",
            "types": ["mean", "state"]
        }
        logging.debug(f"Sending stats request: {json.dumps(stats_request, indent=4)}")
        response = await self.send(stats_request)
        logging.debug(f"Statistics response:  {json.dumps(response, indent=4)}")
        return response
