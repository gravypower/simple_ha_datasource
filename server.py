from flask import Flask, jsonify, request
import requests
import os

app = Flask(__name__)

# Retrieve Home Assistant URL and access token from environment variables
HOME_ASSISTANT_URL = os.getenv('HOME_ASSISTANT_URL')
HOME_ASSISTANT_TOKEN = os.getenv('HOME_ASSISTANT_ACCESS_TOKEN')

headers = {
    "Authorization": f"Bearer {HOME_ASSISTANT_TOKEN}",
    "content-type": "application/json",
}

# Test connection endpoint
@app.route('/', methods=['GET'])
def test_connection():
    return jsonify({"message": "Connection successful"})

# List available metrics endpoint
@app.route('/metrics', methods=['POST'])
def list_metrics():
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "content-type": "application/json",
    }
    
    # URL for the states endpoint
    url = f"{HOME_ASSISTANT_URL}/api/states"
    
    # Make a GET request to the states endpoint
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        # Parse the JSON response
        states = response.json()
        
        # Extract and print the entity_id and state for each entity
        for state in states:
            print(f"Entity ID: {state['entity_id']}, State: {state['state']}")
            
        return states  # or format this as needed
    else:
        print(f"Failed to fetch states: {response.status_code} - {response.text}")
        return []


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
    app.run(debug=True)
