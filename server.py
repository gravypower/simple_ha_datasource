from sanic import Sanic
from sanic.response import json
import os
import logging
import httpx
import json as j
from WebSocketClient import WebSocketClient

app = Sanic(__name__)

# Retrieve Home Assistant URL and access token from environment variables
HOME_ASSISTANT_URL = os.getenv('HOME_ASSISTANT_URL')
HOME_ASSISTANT_TOKEN = os.getenv('HOME_ASSISTANT_TOKEN')

headers = {
    "Authorization": f"Bearer {HOME_ASSISTANT_TOKEN}",
    "content-type": "application/json",
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@app.listener('before_server_start')
async def setup_websocket_client(app, loop):
    global ws_client
    ws_client = WebSocketClient(f"ws://{HOME_ASSISTANT_URL}/api/websocket", HOME_ASSISTANT_TOKEN)
    await ws_client.connect()

# Test connection endpoint
@app.route('/')
async def test_connection(request):
    return json({"message": "Connection successful"})

@app.route('/metrics', methods=['POST'])
async def list_metrics(request):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://{HOME_ASSISTANT_URL}/api/states", headers=headers)

        if response.status_code == 200:
            states = response.json()
            metrics = []

            for state in states:
                attributes = state.get('attributes', {})
                if attributes.get('state_class') == 'measurement':
                    entity_id = state['entity_id']
                    friendly_name = attributes.get('friendly_name', entity_id)
                    metrics.append({"label": friendly_name, "value": entity_id})

            return json(metrics)
        else:
            return json({'error': response.text}, status=response.status_code)


@app.route('/metric-payload-options', methods=['POST'])
async def list_metric_payload_options(request):
    # Your logic here
    return json({"message": "List of metric payload options will be here"})

# Query endpoint (assuming it's a POST method, adjust as needed)
@app.route('/query', methods=['POST'])
async def query_data(request):
    req = request.json

    targets = req['targets']
    start_time = req['range']['from']
    end_time = req['range']['to']

    response = []
    for target in targets:
        statistic_id = target['target']

        try:
            # ... existing logic ...
            statistics = await ws_client.fetch_statistics(statistic_id, start_time, end_time)
            logging.info(f"Statistics received: {j.dumps(statistics, indent=4)}")
            if statistics is None:
                return json({'error': 'Failed to fetch statistics'}, status=500)
            # ... process and return the response ...
        except Exception as e:
            logging.error(f"Error in query_data: {e}")
            return json({'error': 'Internal server error'}, status=500)

        if statistics['success'] and statistic_id in statistics['result']:
            datapoints = [
                [data_point['mean'], data_point['start']]  # Or use 'end' based on your requirement
                for data_point in statistics['result'][statistic_id]
            ]
            response.append({
                "target": statistic_id,
                "datapoints": datapoints
            })
        else:
            logging.error(f"Failed to fetch data for {statistic_id}")

    return json(response)


if __name__ == '__main__':
    port = os.getenv('PORT', 8080)
    app.run(host='0.0.0.0', port=port, debug=True)