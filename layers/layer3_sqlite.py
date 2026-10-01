"""
====================================================================
LAYER 3: SD -> MQTT -> HiveMQ -> SQLite -> Query/Display
====================================================================
Whiteboard Step 3:
- Connects to HiveMQ
- Receives telemetry over MQTT
- Stores persistently into SQLite database
- Performs SQL queries to verify persistence
====================================================================
"""

import time
import json
import sqlite3
import random
from datetime import datetime
import paho.mqtt.client as mqtt

DB_FILE = "layer3_database.db"
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "transformer/layer3/sqlite_stream"

def init_l3_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS l3_telemetry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        oil_temp REAL,
        winding_temp REAL,
        vibration_rms REAL,
        current REAL,
        voltage REAL
    )
    """)
    conn.commit()
    conn.close()

def save_to_sqlite(data):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
    INSERT INTO l3_telemetry (timestamp, oil_temp, winding_temp, vibration_rms, current, voltage)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (data["timestamp"], data["oil_temp"], data["winding_temp"], data["vibration_rms"], data["current"], data["voltage"]))
    conn.commit()
    conn.close()

def query_sqlite():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, timestamp, oil_temp, winding_temp, vibration_rms, current FROM l3_telemetry ORDER BY id DESC LIMIT 5")
    rows = c.fetchall()
    conn.close()
    return rows

def get_client(client_id):
    try:
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    except (AttributeError, TypeError):
        return mqtt.Client(client_id=client_id)

def on_message(client, userdata, msg):
    d = json.loads(msg.payload.decode())
    save_to_sqlite(d)
    print(f"[SQLITE INSERT] Saved reading #{d['timestamp']} into {DB_FILE}")

def run_layer3(cycles=6):
    init_l3_db()
    
    sub = get_client("layer3_sub")
    sub.on_message = on_message
    sub.connect(BROKER, PORT, 60)
    sub.subscribe(TOPIC)
    sub.loop_start()

    pub = get_client("layer3_pub")
    pub.connect(BROKER, PORT, 60)
    pub.loop_start()

    print("="*65)
    print("DEMONSTRATING LAYER 3: SD -> MQTT -> HiveMQ -> SQLite")
    print(f"Database: {DB_FILE} | Broker: {BROKER}")
    print("="*65)

    for i in range(cycles):
        telemetry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "oil_temp": round(54.0 + random.uniform(0.0, 10.0), 1),
            "winding_temp": round(68.0 + random.uniform(0.0, 12.0), 1),
            "vibration_rms": round(0.28 + random.uniform(0.0, 0.1), 2),
            "current": round(62.0 + random.uniform(0.0, 15.0), 1),
            "voltage": round(230.0 + random.uniform(-2.0, 2.0), 1)
        }
        pub.publish(TOPIC, json.dumps(telemetry))
        time.sleep(1.8)

    time.sleep(1.0)
    sub.loop_stop()
    pub.loop_stop()

    print("\n" + "="*65)
    print("VERIFYING PERSISTED SQLITE RECORDS:")
    rows = query_sqlite()
    print(f"{'ID':<4} | {'Timestamp':<20} | {'Oil (C)':<9} | {'Wind (C)':<9} | {'Vib (g)':<8} | {'Current (A)':<10}")
    print("-" * 68)
    for r in rows:
        print(f"{r[0]:<4} | {r[1]:<20} | {r[2]:<9.1f} | {r[3]:<9.1f} | {r[4]:<8.2f} | {r[5]:<10.1f}")
    print("="*65)
    print("Layer 3 demonstration complete.")

if __name__ == "__main__":
    run_layer3()
