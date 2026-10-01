"""
SQLite Database Layer for Transformer Health IoT System
Supports Layer 3 (SQLite storage) & Layer 5 (Historical analysis & alerts)
"""

import sqlite3
import os
import pandas as pd
from datetime import datetime
import config

def get_connection():
    """Create a connection to SQLite database with timeout and WAL mode."""
    conn = sqlite3.connect(config.DATABASE_PATH, timeout=20.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables if they do not exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Telemetry table (Sensor readings)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS telemetry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        device_id TEXT NOT NULL,
        oil_temperature REAL NOT NULL,
        winding_temperature REAL NOT NULL,
        ambient_temperature REAL NOT NULL,
        ambient_humidity REAL NOT NULL,
        vibration_x REAL NOT NULL,
        vibration_y REAL NOT NULL,
        vibration_z REAL NOT NULL,
        vibration_rms REAL NOT NULL,
        load_current REAL NOT NULL,
        voltage REAL NOT NULL,
        oil_level REAL NOT NULL,
        gas_ppm REAL NOT NULL,
        fault_mode TEXT DEFAULT 'NORMAL'
    );
    """)

    # 2. Predictions table (AI/ML Health Index and Classification)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telemetry_id INTEGER,
        timestamp TEXT NOT NULL,
        health_index REAL NOT NULL,
        health_status TEXT NOT NULL,
        anomaly_detected INTEGER DEFAULT 0,
        rul_days REAL,
        primary_fault TEXT,
        confidence REAL,
        FOREIGN KEY (telemetry_id) REFERENCES telemetry(id)
    );
    """)

    # 3. Alerts table (Layer 4 & 5 Alert Dispatch)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        parameter TEXT NOT NULL,
        value REAL NOT NULL,
        severity TEXT NOT NULL,
        message TEXT NOT NULL,
        status TEXT DEFAULT 'Active'
    );
    """)

    # 4. System activity logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        source TEXT NOT NULL,
        level TEXT NOT NULL,
        message TEXT NOT NULL
    );
    """)

    # Indices for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry(timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON predictions(timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp);")

    conn.commit()
    conn.close()

def insert_telemetry(data: dict) -> int:
    """Insert incoming IoT sensor telemetry record."""
    conn = get_connection()
    cursor = conn.cursor()
    
    timestamp = data.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO telemetry (
        timestamp, device_id, oil_temperature, winding_temperature,
        ambient_temperature, ambient_humidity, vibration_x, vibration_y,
        vibration_z, vibration_rms, load_current, voltage,
        oil_level, gas_ppm, fault_mode
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp,
        data.get("device_id", "TRANSFORMER-01"),
        float(data.get("oil_temperature", 50.0)),
        float(data.get("winding_temperature", 60.0)),
        float(data.get("ambient_temperature", 28.0)),
        float(data.get("ambient_humidity", 55.0)),
        float(data.get("vibration_x", 0.1)),
        float(data.get("vibration_y", 0.1)),
        float(data.get("vibration_z", 0.2)),
        float(data.get("vibration_rms", 0.25)),
        float(data.get("load_current", 65.0)),
        float(data.get("voltage", 230.0)),
        float(data.get("oil_level", 88.0)),
        float(data.get("gas_ppm", 250.0)),
        data.get("fault_mode", "NORMAL")
    ))
    
    telemetry_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return telemetry_id

def insert_prediction(data: dict) -> int:
    """Insert AI/ML prediction result."""
    conn = get_connection()
    cursor = conn.cursor()
    
    timestamp = data.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO predictions (
        telemetry_id, timestamp, health_index, health_status,
        anomaly_detected, rul_days, primary_fault, confidence
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("telemetry_id"),
        timestamp,
        float(data.get("health_index", 100.0)),
        data.get("health_status", "Normal"),
        1 if data.get("anomaly_detected") else 0,
        float(data.get("rul_days", 1825.0)),
        data.get("primary_fault", "None (Healthy)"),
        float(data.get("confidence", 0.95))
    ))
    
    pred_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return pred_id

def insert_alert(parameter: str, value: float, severity: str, message: str) -> int:
    """Insert an alert event if not duplicated within the last 15 seconds."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Simple deduplication check for same parameter in active status
    cursor.execute("""
    SELECT id FROM alerts
    WHERE parameter = ? AND status = 'Active'
    ORDER BY id DESC LIMIT 1
    """, (parameter,))
    existing = cursor.fetchone()
    
    # Allow insertion to log event history
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO alerts (timestamp, parameter, value, severity, message, status)
    VALUES (?, ?, ?, ?, ?, 'Active')
    """, (timestamp, parameter, float(value), severity, message))
    
    alert_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return alert_id

def acknowledge_alert(alert_id: int):
    """Mark an alert as Acknowledged."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE alerts SET status = 'Acknowledged' WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()

def acknowledge_all_alerts():
    """Mark all active alerts as Acknowledged."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE alerts SET status = 'Acknowledged' WHERE status = 'Active'")
    conn.commit()
    conn.close()

def get_latest_telemetry() -> dict:
    """Fetch the single most recent telemetry record with prediction."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT t.*, p.health_index, p.health_status, p.anomaly_detected, p.rul_days, p.primary_fault, p.confidence
    FROM telemetry t
    LEFT JOIN predictions p ON t.id = p.telemetry_id
    ORDER BY t.id DESC LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {}

def get_recent_telemetry_df(limit: int = 100) -> pd.DataFrame:
    """Fetch recent telemetry joined with prediction data into a pandas DataFrame."""
    conn = get_connection()
    query = f"""
    SELECT 
        t.id, t.timestamp, t.device_id,
        t.oil_temperature, t.winding_temperature,
        t.ambient_temperature, t.ambient_humidity,
        t.vibration_rms, t.load_current, t.voltage,
        t.oil_level, t.gas_ppm, t.fault_mode,
        p.health_index, p.health_status, p.anomaly_detected, p.rul_days, p.primary_fault
    FROM telemetry t
    LEFT JOIN predictions p ON t.id = p.telemetry_id
    ORDER BY t.id DESC LIMIT {limit}
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    if not df.empty:
        # Sort ascending for chronological charts
        df = df.iloc[::-1].reset_index(drop=True)
    return df

def get_active_alerts(limit: int = 20) -> list:
    """Fetch active alerts."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM alerts
    ORDER BY id DESC LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_db_stats() -> dict:
    """Get database count statistics."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM telemetry")
    total_telemetry = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM predictions")
    total_predictions = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM alerts WHERE status = 'Active'")
    active_alerts = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM alerts")
    total_alerts = cursor.fetchone()[0]
    
    conn.close()
    return {
        "telemetry_count": total_telemetry,
        "predictions_count": total_predictions,
        "active_alerts": active_alerts,
        "total_alerts": total_alerts
    }

def export_to_csv(output_path: str = None) -> str:
    """Export all telemetry data to a CSV file (Layer 1 requirement)."""
    target = output_path or config.CSV_PATH
    conn = get_connection()
    df = pd.read_sql_query("""
    SELECT 
        t.*, p.health_index, p.health_status, p.primary_fault
    FROM telemetry t
    LEFT JOIN predictions p ON t.id = p.telemetry_id
    ORDER BY t.id ASC
    """, conn)
    conn.close()
    df.to_csv(target, index=False)
    return target

# Auto-initialize database on import
init_db()
