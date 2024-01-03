from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Environment variables for Home Assistant
HOME_ASSISTANT_URL = os.getenv('HOME_ASSISTANT_URL', 'http://localhost:8123')  # Update with your Home Assistant URL
HOME_ASSISTANT_TOKEN = os.getenv('HOME_ASSISTANT_TOKEN', 'your_long_lived_access_token')  # Update with your token

@app.route('/')
def root():
    return "Grafana Simple JSON Datasource is running."

@app.route('/search', methods=['POST'])
def search():
    # This endpoint should return the list of entities you want to query from Home Assistant
    # For simplicity, this example returns a static list. You might want to fetch this dynamically.
    return jsonify(["sensor.living_room_temperature", "sensor.living_room_humidity"])

@app.route('/query', methods=['POST'])
def query():
    req = request.get_json()
    
    response = []
    headers = {
        "Authorization": f"Bearer {HOME_ASSISTANT_TOKEN}",
        "content-type": "application/json",
    }

    # Grafana provides the start and end time of the period we want to query
    start_time = req['range']['from']
    end_time = req['range']['to']

    for target in req['targets']:
        entity_id = target['target']
        url = f"{HOME_ASSISTANT_URL}/api/history/period/{start_time}"
        params = {
            'filter_entity_id': entity_id,
            'end_time': end_time
        }
        
        # Query Home Assistant for the entity's historical data
        ha_response = requests.get(url, headers=headers, params=params)
        if ha_response.status_code == 200:
            data = ha_response.json()
            
            # Format the data for Grafana
            datapoints = []
            for state in data[0]:  # data[0] because we're filtering by entity, so only one should be returned
                value = float(state['state'])  # Ensure this is a float or int
                timestamp = datetime.strptime(state['last_changed'], '%Y-%m-%dT%H:%M:%S.%f%z').timestamp() * 1000  # Convert to Unix epoch in milliseconds
                datapoints.append([value, timestamp])
                
            response.append({"target": entity_id, "datapoints": datapoints})
        else:
            # Handle errors or entities not found
            logging.error(f"Failed to fetch data for {entity_id}: {ha_response.status_code} - {ha_response.text}")
            response.append({"target": entity_id, "datapoints": []})

    return jsonify(response)

if __name__ == '__main__':
    port = os.getenv('PORT', 8080)
    app.run(host='0.0.0.0', port=port, debug=True)
