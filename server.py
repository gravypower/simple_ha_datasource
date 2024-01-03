from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

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

    for target in req['targets']:
        entity_id = target['target']
        url = f"{HOME_ASSISTANT_URL}/api/states/{entity_id}"
        
        # Query Home Assistant for the entity's state
        ha_response = requests.get(url, headers=headers)
        if ha_response.status_code == 200:
            data = ha_response.json()
            # Extract the state value and format it for Grafana
            value = float(data['state'])  # Ensure this is a float or int
            timestamp = data['last_updated']  # Use the last_updated timestamp from Home Assistant
            datapoints = [[value, timestamp]]
            response.append({"target": entity_id, "datapoints": datapoints})
        else:
            # Handle errors or entities not found
            response.append({"target": entity_id, "datapoints": []})

    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
