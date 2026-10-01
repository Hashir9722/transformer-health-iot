"""
Central Configuration for IoT Transformer Health Prediction System
Matches Whiteboard Architecture:
Layer 1 -> Layer 2 -> Layer 3 -> Layer 4 -> Layer 5 -> Layer 6
"""

import os

# Base Directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _secret(name, default=""):
    try:
        import streamlit as st
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.getenv(name, default)

# MQTT Configuration (HiveMQ Cloud)
MQTT_BROKER = "50c54ae11f1f4cd3925f256ef57b86ee.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_KEEPALIVE = 60
MQTT_PUBLIC_BROKER = "broker.hivemq.com"
MQTT_USERNAME = _secret("MQTT_USERNAME")
MQTT_PASSWORD = _secret("MQTT_PASSWORD")

# Unique prefix to avoid collision on public HiveMQ broker
# Uses standard project identifier
TOPIC_PREFIX = "transformer_health_iot_mini_proj_suhail"
TOPIC_TELEMETRY = f"{TOPIC_PREFIX}/telemetry"
TOPIC_ALERTS = f"{TOPIC_PREFIX}/alerts"
TOPIC_CONTROL = f"{TOPIC_PREFIX}/control"

# Storage Configuration
DATABASE_PATH = os.path.join(BASE_DIR, "transformer_health.db")
CSV_PATH = os.path.join(BASE_DIR, "transformer_telemetry.csv")
DATASET_PATH = os.path.join(BASE_DIR, "transformer_training_dataset.csv")
MODELS_DIR = os.path.join(BASE_DIR, "models")
MODEL_PATH = os.path.join(MODELS_DIR, "transformer_health_model.pkl")

# Operational Thresholds (IEEE Std C57 & IEC 60599 Transformer Guidelines)
THRESHOLDS = {
    "oil_temperature": {
        "normal_max": 68.0,    # °C
        "warning_max": 85.0,   # °C
        "critical_max": 95.0,  # °C
        "unit": "°C"
    },
    "winding_temperature": {
        "normal_max": 75.0,    # °C
        "warning_max": 95.0,   # °C
        "critical_max": 110.0, # °C
        "unit": "°C"
    },
    "vibration_rms": {
        "normal_max": 0.50,    # g
        "warning_max": 1.10,   # g
        "critical_max": 1.60,  # g
        "unit": "g"
    },
    "load_current": {
        "normal_max": 80.0,    # A
        "warning_max": 105.0,  # A
        "critical_max": 125.0, # A
        "unit": "A"
    },
    "voltage": {
        "min": 200.0,          # V
        "nominal": 230.0,      # V
        "max": 250.0,          # V
        "unit": "V"
    },
    "ambient_humidity": {
        "normal_max": 70.0,    # %
        "warning_max": 85.0,   # %
        "unit": "%"
    },
    "oil_level": {
        "warning_min": 65.0,   # %
        "critical_min": 45.0,  # %
        "unit": "%"
    },
    "gas_ppm": {
        "normal_max": 500.0,   # ppm
        "warning_max": 1000.0, # ppm
        "critical_max": 1400.0,# ppm
        "unit": "ppm"
    }
}

# Health Index Weightings for composite index
WEIGHTS = {
    "winding_temp": 0.25,
    "oil_temp": 0.20,
    "vibration": 0.20,
    "load_current": 0.15,
    "gas_ppm": 0.10,
    "humidity": 0.05,
    "oil_level": 0.05
}

# Web Dashboard Users
USERS = {
    "admin": {
        "password": "admin123",
        "role": "Administrator",
        "name": "Chief Electrical Engineer"
    },
    "operator": {
        "password": "operator123",
        "role": "Substation Operator",
        "name": "Grid Monitoring Operator"
    }
}
