from flask import Flask, jsonify, request, abort
from datetime import datetime
import requests
import os
import logging

app = Flask(__name__)

# Retrieve Home Assistant URL and access token from environment variables
HOME_ASSISTANT_URL = os.getenv('HOME_ASSISTANT_URL')
HOME_ASSISTANT_TOKEN = os.getenv('HOME_ASSISTANT_TOKEN')

headers = {
    "Authorization": f"Bearer {HOME_ASSISTANT_TOKEN}",
    "content-type": "application/json",
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Test connection endpoint
@app.route('/', methods=['GET'])
def test_connection():
    return jsonify({"message": "Connection successful"})

@app.route('/metrics', methods=['POST'])
def list_metrics():
    url = f"{HOME_ASSISTANT_URL}/api/states"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        states = response.json()
        metrics = []

        for state in states:
            attributes = state.get('attributes', {})
            if attributes.get('state_class') == 'measurement':
                entity_id = state['entity_id']
                # Use the friendly name if available, otherwise default to entity_id
                friendly_name = attributes.get('friendly_name', entity_id)
                metrics.append({"label": friendly_name, "value": entity_id})

        return jsonify(metrics)
    else:
        abort(response.status_code, description=response.text)

# List the available payload options endpoint
@app.route('/metric-payload-options', methods=['POST'])
def list_metric_payload_options():
    data = request.json
    return jsonify({"message": "List of metric payload options will be here"})

# Query endpoint (assuming it's a POST method, adjust as needed)
@app.route('/query', methods=['POST'])
def query_data():
    req = request.get_json()
    response = []
    headers = {
        "Authorization": f"Bearer {HOME_ASSISTANT_TOKEN}",
        "content-type": "application/json",
    }

    for target in req['targets']:
        entity_id = target['target']
        url = f"{HOME_ASSISTANT_URL}/api/history/period/{req['range']['from']}"
        params = {
            'filter_entity_id': entity_id,
            'end_time': req['range']['to']
        }
        
        ha_response = requests.get(url, headers=headers, params=params)
        if ha_response.status_code == 200:
            data = ha_response.json()
            datapoints = []
            for state in data[0]:
                try:
                    value = float(state['state'])
                except ValueError:
                    value = None
                
                timestamp = datetime.strptime(state['last_changed'], '%Y-%m-%dT%H:%M:%S.%f%z').timestamp() * 1000
                datapoints.append([value, timestamp])
                
            response.append({"target": entity_id, "datapoints": datapoints})
        else:
            # Return an error response to Grafana
            abort(500, description=f"Failed to fetch data for {entity_id}: {ha_response.status_code} - {ha_response.text}")

    return jsonify(response)

# Add more routes as per your OpenAPI spec

if __name__ == '__main__':
    port = os.getenv('PORT', 8080)
    app.run(host='0.0.0.0', port=port, debug=True)