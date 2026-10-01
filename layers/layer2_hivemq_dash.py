"""
====================================================================
LAYER 2: Synthetic Data -> MQTT -> HiveMQ -> Live Display
====================================================================
Whiteboard Step 2:
- Connects to public HiveMQ cloud broker (broker.hivemq.com)
- Publishes synthetic telemetry
- Subscribes and displays real-time live telemetry stream
====================================================================
"""

import time
import json
import random
from datetime import datetime
import paho.mqtt.client as mqtt

BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "transformer/layer2/hivemq_stream"

def get_client(client_id):
    try:
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    except (AttributeError, TypeError):
        return mqtt.Client(client_id=client_id)

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[HIVEMQ CONNECTED] Connected to {BROKER}:{PORT}")
        client.subscribe(TOPIC)
    else:
        print(f"Connection failed: {rc}")

def on_message(client, userdata, msg):
    d = json.loads(msg.payload.decode())
    print("+-----------------------------------------------------------+")
    print(f"| Timestamp   : {d['timestamp']:<44}|")
    print(f"| Winding Temp: {d['winding_temp']:>5.1f} C   | Oil Temp : {d['oil_temp']:>5.1f} C       |")
    print(f"| Vibration   : {d['vibration_rms']:>5.2f} g    | Current  : {d['current']:>5.1f} A        |")
    print(f"| Voltage     : {d['voltage']:>5.1f} V    | Status   : {d['status']:<14} |")
    print("+-----------------------------------------------------------+\n")

def run_layer2(cycles=5):
    sub = get_client(f"layer2_sub_{random.randint(100, 999)}")
    sub.on_connect = on_connect
    sub.on_message = on_message
    sub.connect(BROKER, PORT, 60)
    sub.loop_start()

    pub = get_client(f"layer2_pub_{random.randint(100, 999)}")
    pub.connect(BROKER, PORT, 60)
    pub.loop_start()

    print("="*65)
    print("DEMONSTRATING LAYER 2: SD -> MQTT -> HiveMQ -> Live Stream")
    print(f"Connecting to HiveMQ Broker: {BROKER}...")
    print("="*65)

    time.sleep(1.0)
    for i in range(cycles):
        telemetry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "oil_temp": round(52.0 + random.uniform(0.0, 12.0), 1),
            "winding_temp": round(64.0 + random.uniform(0.0, 18.0), 1),
            "vibration_rms": round(0.24 + random.uniform(0.0, 0.15), 2),
            "current": round(60.0 + random.uniform(0.0, 20.0), 1),
            "voltage": round(230.0 + random.uniform(-3.0, 3.0), 1),
            "status": "NORMAL"
        }
        pub.publish(TOPIC, json.dumps(telemetry))
        time.sleep(1.5)

    time.sleep(1.0)
    sub.loop_stop()
    pub.loop_stop()
    print("Layer 2 demonstration finished successfully.")

if __name__ == "__main__":
    run_layer2()
