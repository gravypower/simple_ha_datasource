from sanic import Sanic
from sanic.response import json
import os
import logging
import httpx
import json as j
from dateutil import parser
from WebSocketClient import WebSocketClient

app = Sanic(__name__)

# Retrieve Home Assistant URL and access token from environment variables
HOME_ASSISTANT_URL = os.getenv('HOME_ASSISTANT_URL')
HOME_ASSISTANT_TOKEN = os.getenv('HOME_ASSISTANT_TOKEN')

headers = {
    "Authorization": f"Bearer {HOME_ASSISTANT_TOKEN}",
    "content-type": "application/json",
}

# Retrieve the logging level from an environment variable
logging_level_str = os.getenv('LOGGING_LEVEL', 'DEBUG')

# Translate the logging level from string to logging module constant
logging_level = getattr(logging, logging_level_str.upper(), logging.DEBUG)

# Apply the logging configuration with the retrieved level
logging.basicConfig(level=logging_level, format='%(asctime)s - %(levelname)s - %(message)s')

@app.listener('before_server_start')
async def setup_websocket_client(app, loop):
    global ws_client
    haWebsocketUrl = f"wss://{HOME_ASSISTANT_URL}/api/websocket"
    ws_client = WebSocketClient(haWebsocketUrl, HOME_ASSISTANT_TOKEN)
    logging.info(f'haWebsocketUrl: {haWebsocketUrl}')
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

@app.route('/query', methods=['POST'])
async def query_data(request):
    req = request.json
    start_time_str = req['range']['from']
    end_time_str = req['range']['to']

    # Convert string to datetime objects and then to ISO format
    start_time = format_datetime(start_time_str)
    end_time = format_datetime(end_time_str)

    # Extract all entity_ids from the request
    entity_ids = [target['target'] for target in req['targets']]

    # Fetch statistics for all ids at once
    statistics = await ws_client.fetch_statistics(entity_ids, start_time, end_time)
    logging.debug(f"Statistics received: {j.dumps(statistics, indent=4)}")

    # Process the response and construct the output
    response = []
    if statistics and statistics.get('success', False):
        for statistic_id in entity_ids:
            # Assuming your API returns data in a format that needs to be processed here
            # This part highly depends on the actual structure of the response
            datapoints = [[dp['mean'], dp['start']] for dp in statistics['result'][statistic_id]]
            response.append({"target": statistic_id, "datapoints": datapoints})
    else:
        logging.error("Failed to fetch data")

    return json(response)

def format_datetime(datetime_str):
    # Parse the datetime string to a datetime object
    dt = parser.parse(datetime_str)
    
    # Format the datetime object to the specified format
    # Note: The '%f' directive represents microseconds, which we limit to 3 digits for milliseconds
    formatted_datetime = dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    
    return formatted_datetime

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)