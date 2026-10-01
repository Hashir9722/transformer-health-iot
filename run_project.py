"""
Master Runner for IoT Transformer Health Prediction System
Starts:
1. SQLite Database & AI/ML Model verification
2. Synthetic IoT Publisher (DHT11 & MPU6050 Simulator -> HiveMQ)
3. MQTT Telemetry Subscriber (HiveMQ -> SQLite -> ML Inference -> Alert Dispatch)
4. Streamlit Dashboard (Login -> Real-time Gauges -> Alarms)
"""

import subprocess
import sys
import time
import os
import argparse
import database
from ml_model import get_predictor
from generate_dataset import generate_transformer_dataset
from datetime import datetime

def check_and_seed_data():
    """Ensure database exists and has seed data for immediate demonstration."""
    database.init_db()
    stats = database.get_db_stats()
    if stats["telemetry_count"] < 15:
        print("[INIT] Seeding initial transformer telemetry records into SQLite...")
        predictor = get_predictor()
        df_seed = generate_transformer_dataset(30)
        for _, row in df_seed.iterrows():
            d = dict(row)
            d["device_id"] = "TRANSFORMER-ESP32-01"
            d["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            d["fault_mode"] = "NORMAL"
            tid = database.insert_telemetry(d)
            pred = predictor.predict(d)
            pred["telemetry_id"] = tid
            pred["timestamp"] = d["timestamp"]
            database.insert_prediction(pred)
        print(f"[INIT] Seeded {len(df_seed)} baseline records successfully.")

def main():
    parser = argparse.ArgumentParser(description="Master Launcher for IoT Transformer Health Project")
    parser.add_argument("--component", type=str, default="all",
                        choices=["all", "dashboard", "publisher", "subscriber"],
                        help="Choose which component to run")
    args = parser.parse_args()

    print("="*70)
    print("  ⚡ IoT TRANSFORMER HEALTH PREDICTION SYSTEM (SOFTWARE SUITE)")
    print("  Architecture: Layer 1 -> Layer 2 -> Layer 3 -> Layer 4 -> Layer 5")
    print("="*70)

    # 1. Model & DB check
    print("[1/3] Verifying AI/ML Model & SQLite Database...")
    check_and_seed_data()
    print("[1/3] AI/ML Model & Database ready.")

    python_executable = sys.executable

    processes = []

    try:
        if args.component in ["all", "subscriber"]:
            print("[2/3] Launching Background MQTT Subscriber (HiveMQ -> SQLite -> ML)...")
            sub_proc = subprocess.Popen([python_executable, "mqtt_subscriber.py"])
            processes.append(sub_proc)
            time.sleep(1.0)

        if args.component in ["all", "publisher"]:
            print("[3/3] Launching Synthetic IoT Publisher (Simulating ESP32)...")
            pub_proc = subprocess.Popen([python_executable, "synthetic_publisher.py", "--interval", "2.5"])
            processes.append(pub_proc)
            time.sleep(1.0)

        if args.component in ["all", "dashboard"]:
            print("\n" + "="*70)
            print("  🌐 Starting Streamlit Dashboard...")
            print("  Default Credentials: admin / admin123  OR  operator / operator123")
            print("="*70 + "\n")
            
            # Launch streamlit
            cmd = [python_executable, "-m", "streamlit", "run", "app.py", "--server.port", "8501"]
            dash_proc = subprocess.Popen(cmd)
            processes.append(dash_proc)

        # Wait on processes
        for p in processes:
            p.wait()

    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Terminating all background services...")
        for p in processes:
            try:
                p.terminate()
            except:
                pass
        print("[SHUTDOWN] All services stopped cleanly.")

if __name__ == "__main__":
    main()
