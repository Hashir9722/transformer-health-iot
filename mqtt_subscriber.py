"""
MQTT Telemetry Subscriber & AI/ML Prediction Engine
Connects: HiveMQ -> SQLite -> AI/ML Health Model -> Alert Dispatcher
Implements Layer 1 (CSV), Layer 3 (SQLite), and Layer 5 (AI/ML + Alerting)
"""

import json
import os
import random
import csv
from datetime import datetime
import paho.mqtt.client as mqtt

import config
import database
from ml_model import get_predictor

# Ensure CSV header exists for Layer 1 logging
def init_csv_log():
    if not os.path.exists(config.CSV_PATH):
        with open(config.CSV_PATH, mode="w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "device_id", "oil_temperature", "winding_temperature",
                "ambient_temperature", "ambient_humidity", "vibration_rms",
                "load_current", "voltage", "oil_level", "gas_ppm",
                "health_index", "health_status", "primary_fault"
            ])

def append_to_csv(telemetry: dict, prediction: dict):
    """Log telemetry and prediction to CSV file (Layer 1 requirement)."""
    with open(config.CSV_PATH, mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            telemetry.get("timestamp"),
            telemetry.get("device_id"),
            telemetry.get("oil_temperature"),
            telemetry.get("winding_temperature"),
            telemetry.get("ambient_temperature"),
            telemetry.get("ambient_humidity"),
            telemetry.get("vibration_rms"),
            telemetry.get("load_current"),
            telemetry.get("voltage"),
            telemetry.get("oil_level"),
            telemetry.get("gas_ppm"),
            prediction.get("health_index"),
            prediction.get("health_status"),
            prediction.get("primary_fault")
        ])

def get_mqtt_client(client_id: str):
    """Instantiate paho MQTT client compatible with v1 and v2."""
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    except (AttributeError, TypeError):
        client = mqtt.Client(client_id=client_id)
    return client

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[MQTT Subscriber] Connected successfully to HiveMQ broker: {config.MQTT_BROKER}")
        client.subscribe(config.TOPIC_TELEMETRY)
        print(f"[MQTT Subscriber] Subscribed to telemetry topic: {config.TOPIC_TELEMETRY}")
        print("Ready to process incoming transformer telemetry...\n")
    else:
        print(f"[MQTT Subscriber] Connection failed with code {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
    except Exception as e:
        print(f"[MQTT Subscriber] Failed to decode JSON message: {e}")
        return

    # 1. Insert Telemetry into SQLite (Layer 3)
    telemetry_id = database.insert_telemetry(payload)

    # 2. Run AI/ML Health Prediction Pipeline (Layer 5)
    predictor = get_predictor()
    pred = predictor.predict(payload)
    pred["telemetry_id"] = telemetry_id
    pred["timestamp"] = payload.get("timestamp")
    
    # 3. Store Prediction in SQLite (Layer 5)
    database.insert_prediction(pred)

    # 4. Append to CSV (Layer 1)
    append_to_csv(payload, pred)

    # 5. Alert Evaluation & Dispatch (Layer 4 & Layer 5)
    health_status = pred.get("health_status", "Normal")
    health_index = pred.get("health_index", 100.0)
    fault_causes = pred.get("fault_causes", [])

    alerts_triggered = []
    
    if health_status == "Critical":
        alert_msg = f"CRITICAL: Health Index dropped to {health_index:.1f}%. Root cause: {pred.get('primary_fault')}"
        database.insert_alert("HEALTH_INDEX", health_index, "Critical", alert_msg)
        alerts_triggered.append(alert_msg)

    elif health_status == "Warning":
        alert_msg = f"WARNING: Transformer degradation detected ({health_index:.1f}%). Cause: {pred.get('primary_fault')}"
        database.insert_alert("HEALTH_INDEX", health_index, "Warning", alert_msg)
        alerts_triggered.append(alert_msg)

    # Individual critical parameter alerts
    for cause in fault_causes:
        if "Critical" in cause or "Severe" in cause:
            database.insert_alert("PARAM_FAULT", 0.0, "Critical", cause)
            alerts_triggered.append(cause)

    # If alerts exist, publish them to MQTT Alert topic (Layer 4/5 integration for Node-RED)
    if alerts_triggered:
        alert_payload = {
            "timestamp": payload.get("timestamp"),
            "device_id": payload.get("device_id"),
            "health_index": health_index,
            "health_status": health_status,
            "primary_fault": pred.get("primary_fault"),
            "alerts": alerts_triggered
        }
        client.publish(config.TOPIC_ALERTS, json.dumps(alert_payload), qos=0)

    # Console display
    status_tag = "[OK]  " if health_status == "Normal" else ("[WARN]" if health_status == "Warning" else "[CRIT]")
    print(f"[{payload.get('timestamp')}] {status_tag} Health: {health_index:>5.1f}% [{health_status:<8}] | "
          f"RUL: {pred.get('rul_days'):>5.0f}d | "
          f"Wind: {payload.get('winding_temperature'):>5.1f} C | "
          f"Vib: {payload.get('vibration_rms'):>4.2f}g | "
          f"Fault: {pred.get('primary_fault')}")
    
    if alerts_triggered:
        print(f"   >>> ALARM TRIGGERED: {alerts_triggered[0]}")

def run_subscriber():
    """Main subscriber process."""
    init_csv_log()
    database.init_db()

    client_id = f"transformer_sub_{random.randint(1000, 9999)}"
    client = get_mqtt_client(client_id)
    client.on_connect = on_connect
    client.on_message = on_message

    print("="*65)
    print("  IoT Transformer MQTT Subscriber & Health Prediction Engine")
    print(f"  Broker: {config.MQTT_BROKER}:{config.MQTT_PORT}")
    print(f"  Topic : {config.TOPIC_TELEMETRY}")
    print(f"  Alerts: {config.TOPIC_ALERTS}")
    print(f"  DB    : {config.DATABASE_PATH}")
    print("="*65)

    try:
        client.connect(config.MQTT_BROKER, config.MQTT_PORT, config.MQTT_KEEPALIVE)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nSubscriber stopped by user.")
    finally:
        client.disconnect()
        print("MQTT client disconnected.")

if __name__ == "__main__":
    run_subscriber()
