"""
====================================================================
LAYER 1: Synthetic Data -> MQTT -> CSV -> Display
====================================================================
Whiteboard Step 1:
- Generates synthetic sensor telemetry
- Publishes over MQTT
- Subscribes and logs directly to CSV file
- Displays summary
====================================================================
"""

import time
import json
import csv
import os
import random
from datetime import datetime
import paho.mqtt.client as mqtt

CSV_FILE = "layer1_telemetry.csv"
TOPIC = "transformer/layer1/telemetry"
BROKER = "broker.hivemq.com"
PORT = 1883

def get_client(client_id):
    try:
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    except (AttributeError, TypeError):
        return mqtt.Client(client_id=client_id)

def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode="w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "oil_temp", "winding_temp", "vibration_rms", "current", "voltage"])

def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())
    with open(CSV_FILE, mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            data["timestamp"], data["oil_temp"], data["winding_temp"],
            data["vibration_rms"], data["current"], data["voltage"]
        ])
    print(f"[LAYER 1 CSV LOGGED] {data['timestamp']} | Oil: {data['oil_temp']} C | Winding: {data['winding_temp']} C | Vib: {data['vibration_rms']}g -> Saved to {CSV_FILE}")

def run_layer1(cycles=10):
    init_csv()
    
    # 1. Subscriber
    sub_client = get_client("layer1_sub")
    sub_client.on_message = on_message
    sub_client.connect(BROKER, PORT, 60)
    sub_client.subscribe(TOPIC)
    sub_client.loop_start()

    # 2. Publisher
    pub_client = get_client("layer1_pub")
    pub_client.connect(BROKER, PORT, 60)
    pub_client.loop_start()

    print("="*60)
    print("DEMONSTRATING LAYER 1: Synthetic Data -> MQTT -> CSV")
    print(f"Broker: {BROKER} | Topic: {TOPIC} | Output: {CSV_FILE}")
    print("="*60)

    for i in range(cycles):
        telemetry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "oil_temp": round(50.0 + random.uniform(0.0, 15.0), 2),
            "winding_temp": round(62.0 + random.uniform(0.0, 20.0), 2),
            "vibration_rms": round(0.20 + random.uniform(0.0, 0.25), 3),
            "current": round(55.0 + random.uniform(0.0, 25.0), 2),
            "voltage": round(230.0 + random.uniform(-4.0, 4.0), 2)
        }
        pub_client.publish(TOPIC, json.dumps(telemetry))
        time.sleep(1.5)

    time.sleep(1.0)
    sub_client.loop_stop()
    pub_client.loop_stop()
    print("="*60)
    print(f"Layer 1 demonstration complete. Telemetry recorded in {CSV_FILE}")
    print("="*60)

if __name__ == "__main__":
    run_layer1()
