"""
Synthetic IoT Telemetry Publisher (Simulates ESP32 with DHT11, MPU6050, CT, RTD)
Publishes real-time telemetry to HiveMQ MQTT Broker.
Supports dynamic fault injection via MQTT control topic or CLI.
"""

import time
import json
import random
import math
import argparse
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
import paho.mqtt.client as mqtt
import config

# Global simulation state
current_mode = "NORMAL"

def get_mqtt_client(client_id: str):
    """Instantiate paho MQTT client compatible with v1 and v2."""
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    except (AttributeError, TypeError):
        client = mqtt.Client(client_id=client_id)
    return client

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[MQTT Publisher] Connected successfully to HiveMQ broker: {config.MQTT_BROKER}")
        # Subscribe to control topic to receive live commands from dashboard
        client.subscribe(config.TOPIC_CONTROL)
        print(f"[MQTT Publisher] Subscribed to control topic: {config.TOPIC_CONTROL}")
    else:
        print(f"[MQTT Publisher] Connection failed with code {rc}")

def on_message(client, userdata, msg):
    global current_mode
    try:
        payload = json.loads(msg.payload.decode())
        if "mode" in payload:
            old_mode = current_mode
            current_mode = payload["mode"].upper()
            print(f"\n[CONTROL EVENT] Fault Mode changed from {old_mode} -> {current_mode}\n")
    except Exception as e:
        print(f"[MQTT Publisher] Error parsing control message: {e}")

def generate_telemetry_reading(step: int, mode: str) -> dict:
    """Generate realistic physical telemetry with micro-fluctuations."""
    # Sine wave for daily temperature variation
    time_factor = math.sin(step * 0.1)
    
    # 1. Base ambient conditions (Simulating DHT11)
    amb_temp = 28.0 + 3.0 * time_factor + random.uniform(-0.5, 0.5)
    amb_hum = 55.0 - 5.0 * time_factor + random.uniform(-1.0, 1.0)
    
    # 2. Voltage (Normal Grid fluctuation 227 - 233 V)
    voltage = 230.0 + random.uniform(-3.0, 3.0)
    
    if mode == "NORMAL":
        current = 62.0 + 8.0 * time_factor + random.uniform(-2.0, 2.0)
        oil_temp = amb_temp + 22.0 + (current / 80.0) * 10.0 + random.uniform(-0.8, 0.8)
        winding_temp = oil_temp + 12.0 + (current / 80.0) * 6.0 + random.uniform(-0.8, 0.8)
        vib_rms = 0.22 + random.uniform(-0.04, 0.05)
        oil_level = 88.0 + random.uniform(-0.5, 0.5)
        gas_ppm = 220.0 + random.uniform(-10.0, 15.0)

    elif mode == "OVERHEATING":
        # Thermal fault: Cooling fan failure / severe load heat accumulation
        current = 82.0 + random.uniform(-3.0, 4.0)
        oil_temp = 92.5 + random.uniform(0.0, 4.5)
        winding_temp = oil_temp + 22.0 + random.uniform(1.0, 4.0)
        vib_rms = 0.45 + random.uniform(-0.05, 0.08)
        oil_level = 84.0 + random.uniform(-1.0, 1.0)
        gas_ppm = 480.0 + random.uniform(-20.0, 40.0)

    elif mode == "VIBRATION_FAULT":
        # Mechanical fault: Winding clamping looseness / core deformation (MPU6050 anomaly)
        current = 68.0 + random.uniform(-2.0, 2.0)
        oil_temp = amb_temp + 25.0 + random.uniform(-1.0, 1.0)
        winding_temp = oil_temp + 14.0 + random.uniform(-1.0, 1.0)
        vib_rms = 1.38 + random.uniform(0.05, 0.35)  # Severe vibration > 1.2g
        oil_level = 86.0 + random.uniform(-0.5, 0.5)
        gas_ppm = 310.0 + random.uniform(-15.0, 20.0)

    elif mode == "OVERLOAD":
        # Electrical overload fault
        current = 122.0 + random.uniform(2.0, 12.0)  # > 115 A
        oil_temp = 88.0 + random.uniform(1.0, 5.0)
        winding_temp = oil_temp + 26.0 + random.uniform(2.0, 6.0)
        vib_rms = 0.75 + random.uniform(0.05, 0.20)
        voltage = 212.0 - random.uniform(1.0, 6.0)   # Voltage sag
        oil_level = 83.0 + random.uniform(-0.5, 0.5)
        gas_ppm = 620.0 + random.uniform(10.0, 50.0)

    elif mode == "LOW_OIL":
        # Radiator oil leakage
        current = 65.0 + random.uniform(-2.0, 2.0)
        oil_level = 38.0 - random.uniform(0.0, 5.0)  # Critical low
        oil_temp = 89.0 + random.uniform(1.0, 4.0)   # Decreased heat dissipation
        winding_temp = oil_temp + 25.0 + random.uniform(1.0, 5.0)
        vib_rms = 0.55 + random.uniform(-0.05, 0.10)
        gas_ppm = 510.0 + random.uniform(-10.0, 30.0)

    elif mode == "GAS_ARCING":
        # Internal partial discharge / arcing in insulation
        current = 75.0 + random.uniform(-2.0, 3.0)
        oil_temp = 78.0 + random.uniform(1.0, 4.0)
        winding_temp = oil_temp + 18.0 + random.uniform(1.0, 4.0)
        vib_rms = 0.65 + random.uniform(0.0, 0.15)
        oil_level = 82.0 + random.uniform(-0.5, 0.5)
        gas_ppm = 1650.0 + random.uniform(50.0, 300.0) # > 1200 ppm critical

    else:
        # Fallback normal
        current = 65.0
        oil_temp = 55.0
        winding_temp = 68.0
        vib_rms = 0.25
        oil_level = 88.0
        gas_ppm = 250.0

    # Calculate MPU6050 3-axis accelerometer values from RMS
    vib_x = vib_rms * 0.42 + random.uniform(-0.02, 0.02)
    vib_y = vib_rms * 0.45 + random.uniform(-0.02, 0.02)
    vib_z = math.sqrt(max(0.001, vib_rms**2 - vib_x**2 - vib_y**2))

    reading = {
        "timestamp": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
        "device_id": "TRANSFORMER-ESP32-01",
        "oil_temperature": round(oil_temp, 2),
        "winding_temperature": round(winding_temp, 2),
        "ambient_temperature": round(amb_temp, 2),
        "ambient_humidity": round(amb_hum, 2),
        "vibration_x": round(vib_x, 3),
        "vibration_y": round(vib_y, 3),
        "vibration_z": round(vib_z, 3),
        "vibration_rms": round(vib_rms, 3),
        "load_current": round(current, 2),
        "voltage": round(voltage, 2),
        "oil_level": round(oil_level, 2),
        "gas_ppm": round(gas_ppm, 2),
        "fault_mode": mode
    }
    return reading

def run_publisher(interval=2.0, default_mode="NORMAL", iterations=None):
    """Publish telemetry loop."""
    global current_mode
    current_mode = default_mode
    
    client_id = f"transformer_sim_pub_{random.randint(1000, 9999)}"
    client = get_mqtt_client(client_id)
    client.on_connect = on_connect
    client.on_message = on_message
    
    print("="*65)
    print(f"  IoT Transformer Telemetry Publisher (ESP32 Simulator)")
    print(f"  Broker : {config.MQTT_BROKER}:{config.MQTT_PORT}")
    print(f"  Topic  : {config.TOPIC_TELEMETRY}")
    print(f"  Initial Mode: {current_mode} | Interval: {interval}s")
    print("="*65)
    
    try:
        client.connect(config.MQTT_BROKER, config.MQTT_PORT, config.MQTT_KEEPALIVE)
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}")
        return

    client.loop_start()
    
    step = 0
    try:
        while True:
            if iterations is not None and step >= iterations:
                break
                
            step += 1
            payload = generate_telemetry_reading(step, current_mode)
            payload_json = json.dumps(payload)
            
            client.publish(config.TOPIC_TELEMETRY, payload_json, qos=0)
            
            # Formatted status output
            print(f"[{payload['timestamp']}] Mode: {payload['fault_mode']:<14} | "
                  f"Wind: {payload['winding_temperature']:>5.1f} C | "
                  f"Oil: {payload['oil_temperature']:>5.1f} C | "
                  f"Vib: {payload['vibration_rms']:>4.2f}g | "
                  f"Curr: {payload['load_current']:>5.1f}A | "
                  f"Gas: {payload['gas_ppm']:>5.0f}ppm")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\nPublisher stopped by user.")
    finally:
        client.loop_stop()
        client.disconnect()
        print("MQTT client disconnected.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IoT Transformer Telemetry Publisher")
    parser.add_argument("--interval", type=float, default=2.0, help="Publish interval in seconds")
    parser.add_argument("--mode", type=str, default="NORMAL", 
                        choices=["NORMAL", "OVERHEATING", "VIBRATION_FAULT", "OVERLOAD", "LOW_OIL", "GAS_ARCING"],
                        help="Initial fault simulation mode")
    parser.add_argument("--iterations", type=int, default=None, help="Number of telemetry cycles to publish")
    args = parser.parse_args()
    
    run_publisher(interval=args.interval, default_mode=args.mode, iterations=args.iterations)
