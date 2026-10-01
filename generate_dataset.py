"""
Synthetic Dataset Generator for Transformer Health Prediction
Generates realistic transformer sensor data across Normal, Warning, and Critical operating conditions.
"""

import numpy as np
import pandas as pd
import os
import config

def calculate_transformer_health(oil_temp, winding_temp, vib_rms, current, voltage, humidity, oil_lvl, gas):
    """
    Calculate Transformer Health Index (THI 0-100) using IEEE/CIGRE weighted degradation principles.
    """
    # 1. Thermal penalty (Winding & Oil)
    # Baseline normal: Winding <= 75C, Oil <= 68C
    p_wind = np.clip((winding_temp - 70.0) / 40.0, 0.0, 1.0) * 100.0
    p_oil = np.clip((oil_temp - 65.0) / 35.0, 0.0, 1.0) * 100.0
    
    # 2. Mechanical / Vibration penalty (Core/winding looseness)
    # Baseline normal: <= 0.45g
    p_vib = np.clip((vib_rms - 0.40) / 1.20, 0.0, 1.0) * 100.0
    
    # 3. Electrical loading penalty
    # Baseline normal: <= 80A
    p_curr = np.clip((current - 75.0) / 50.0, 0.0, 1.0) * 100.0
    
    # Voltage deviation penalty
    v_dev = np.abs(voltage - 230.0)
    p_volt = np.clip((v_dev - 15.0) / 25.0, 0.0, 1.0) * 100.0
    
    # 4. Oil Quality / Dissolved Gas penalty (TDCG ppm)
    # Baseline normal: <= 400 ppm
    p_gas = np.clip((gas - 350.0) / 950.0, 0.0, 1.0) * 100.0
    
    # 5. Oil level penalty
    # Baseline normal: >= 80%
    p_oillvl = np.clip((75.0 - oil_lvl) / 35.0, 0.0, 1.0) * 100.0
    
    # 6. Humidity penalty (Moisture ingress)
    p_hum = np.clip((humidity - 65.0) / 30.0, 0.0, 1.0) * 100.0
    
    # Weighted total penalty
    w = config.WEIGHTS
    total_penalty = (
        w["winding_temp"] * p_wind +
        w["oil_temp"] * p_oil +
        w["vibration"] * p_vib +
        w["load_current"] * p_curr +
        0.05 * p_volt +
        w["gas_ppm"] * p_gas +
        w["oil_level"] * p_oillvl +
        w["humidity"] * p_hum
    )
    
    # Non-linear critical multiplier if multiple extreme parameters coincide
    if p_wind > 80.0 and p_oil > 80.0:
        total_penalty = min(100.0, total_penalty * 1.25)
    if p_vib > 80.0 and p_curr > 80.0:
        total_penalty = min(100.0, total_penalty * 1.20)
        
    health_index = np.clip(100.0 - total_penalty, 0.0, 100.0)
    return health_index

def generate_transformer_dataset(n_samples=4000, random_state=42):
    """Generate balanced dataset across operational health regimes."""
    np.random.seed(random_state)
    
    # Ratios: 60% Normal, 25% Warning, 15% Critical
    n_normal = int(n_samples * 0.60)
    n_warning = int(n_samples * 0.25)
    n_critical = n_samples - n_normal - n_warning
    
    records = []
    
    # 1. Normal Operations
    for _ in range(n_normal):
        amb_temp = np.random.uniform(22.0, 36.0)
        amb_hum = np.random.uniform(35.0, 65.0)
        oil_temp = amb_temp + np.random.uniform(18.0, 30.0)
        winding_temp = oil_temp + np.random.uniform(8.0, 16.0)
        vib_x = np.random.normal(0.12, 0.04)
        vib_y = np.random.normal(0.14, 0.04)
        vib_z = np.random.normal(0.20, 0.05)
        vib_rms = np.sqrt(vib_x**2 + vib_y**2 + vib_z**2)
        current = np.random.uniform(45.0, 78.0)
        voltage = np.random.normal(230.0, 3.5)
        oil_level = np.random.uniform(82.0, 96.0)
        gas_ppm = np.random.uniform(120.0, 380.0)
        
        thi = calculate_transformer_health(oil_temp, winding_temp, vib_rms, current, voltage, amb_hum, oil_level, gas_ppm)
        rul = np.clip(np.random.uniform(1500, 3650) * (thi / 100.0), 300, 3650)
        
        records.append({
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
            "health_index": round(thi, 2),
            "health_status": "Normal",
            "primary_fault": "None (Healthy)",
            "rul_days": round(rul, 1)
        })
        
    # 2. Warning Regimes (Moderate faults: elevated temp, mild vibration, high load)
    for _ in range(n_warning):
        fault_type = np.random.choice([
            "Elevated Temperature", "Mechanical Looseness (Vibration)",
            "High Load Current", "Moisture Ingress / Gas Buildup"
        ])
        
        amb_temp = np.random.uniform(25.0, 40.0)
        amb_hum = np.random.uniform(45.0, 78.0)
        voltage = np.random.normal(228.0, 6.0)
        oil_level = np.random.uniform(68.0, 84.0)
        gas_ppm = np.random.uniform(350.0, 750.0)
        
        if fault_type == "Elevated Temperature":
            oil_temp = np.random.uniform(72.0, 86.0)
            winding_temp = oil_temp + np.random.uniform(15.0, 22.0)
            vib_rms = np.random.uniform(0.35, 0.65)
            current = np.random.uniform(75.0, 95.0)
        elif fault_type == "Mechanical Looseness (Vibration)":
            oil_temp = np.random.uniform(55.0, 72.0)
            winding_temp = oil_temp + np.random.uniform(10.0, 18.0)
            vib_rms = np.random.uniform(0.60, 1.10)
            current = np.random.uniform(60.0, 85.0)
        elif fault_type == "High Load Current":
            current = np.random.uniform(90.0, 112.0)
            oil_temp = np.random.uniform(68.0, 82.0)
            winding_temp = oil_temp + np.random.uniform(18.0, 25.0)
            vib_rms = np.random.uniform(0.40, 0.75)
        else: # Moisture / Gas
            amb_hum = np.random.uniform(75.0, 92.0)
            gas_ppm = np.random.uniform(650.0, 1100.0)
            oil_temp = np.random.uniform(60.0, 75.0)
            winding_temp = oil_temp + np.random.uniform(12.0, 20.0)
            vib_rms = np.random.uniform(0.30, 0.60)
            current = np.random.uniform(60.0, 85.0)
            
        vib_x = vib_rms * np.random.uniform(0.3, 0.5)
        vib_y = vib_rms * np.random.uniform(0.3, 0.5)
        vib_z = np.sqrt(max(0.001, vib_rms**2 - vib_x**2 - vib_y**2))
        
        thi = calculate_transformer_health(oil_temp, winding_temp, vib_rms, current, voltage, amb_hum, oil_level, gas_ppm)
        # Force into warning boundary if edge case
        thi = np.clip(thi, 50.0, 79.0)
        rul = np.clip(np.random.uniform(300, 1200) * (thi / 100.0), 90, 1200)
        
        records.append({
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
            "health_index": round(thi, 2),
            "health_status": "Warning",
            "primary_fault": fault_type,
            "rul_days": round(rul, 1)
        })
        
    # 3. Critical Regimes (Dangerous conditions: severe overheating, heavy vibration, severe overload)
    for _ in range(n_critical):
        fault_type = np.random.choice([
            "Severe Thermal Overheating", "Severe Core Vibration Fault",
            "Heavy Electrical Overload", "Severe Arcing & Gas Degradation", "Critical Low Oil"
        ])
        
        amb_temp = np.random.uniform(28.0, 44.0)
        amb_hum = np.random.uniform(50.0, 95.0)
        voltage = np.random.choice([np.random.uniform(180.0, 202.0), np.random.uniform(254.0, 270.0)])
        oil_level = np.random.uniform(40.0, 75.0)
        gas_ppm = np.random.uniform(800.0, 2000.0)
        
        if fault_type == "Severe Thermal Overheating":
            oil_temp = np.random.uniform(92.0, 115.0)
            winding_temp = oil_temp + np.random.uniform(20.0, 35.0)
            vib_rms = np.random.uniform(0.50, 0.95)
            current = np.random.uniform(85.0, 120.0)
        elif fault_type == "Severe Core Vibration Fault":
            oil_temp = np.random.uniform(70.0, 90.0)
            winding_temp = oil_temp + np.random.uniform(15.0, 25.0)
            vib_rms = np.random.uniform(1.25, 2.50)
            current = np.random.uniform(75.0, 105.0)
        elif fault_type == "Heavy Electrical Overload":
            current = np.random.uniform(115.0, 150.0)
            oil_temp = np.random.uniform(88.0, 108.0)
            winding_temp = oil_temp + np.random.uniform(22.0, 38.0)
            vib_rms = np.random.uniform(0.70, 1.40)
        elif fault_type == "Critical Low Oil":
            oil_level = np.random.uniform(25.0, 48.0)
            oil_temp = np.random.uniform(85.0, 105.0)
            winding_temp = oil_temp + np.random.uniform(25.0, 40.0)
            vib_rms = np.random.uniform(0.40, 0.90)
            current = np.random.uniform(65.0, 95.0)
        else: # Severe Arcing & Gas Degradation
            gas_ppm = np.random.uniform(1300.0, 2800.0)
            oil_temp = np.random.uniform(80.0, 100.0)
            winding_temp = oil_temp + np.random.uniform(18.0, 30.0)
            vib_rms = np.random.uniform(0.60, 1.20)
            current = np.random.uniform(70.0, 105.0)
            
        vib_x = vib_rms * np.random.uniform(0.3, 0.5)
        vib_y = vib_rms * np.random.uniform(0.3, 0.5)
        vib_z = np.sqrt(max(0.001, vib_rms**2 - vib_x**2 - vib_y**2))
        
        thi = calculate_transformer_health(oil_temp, winding_temp, vib_rms, current, voltage, amb_hum, oil_level, gas_ppm)
        thi = np.clip(thi, 5.0, 49.0)
        rul = np.clip(np.random.uniform(10, 150) * (thi / 50.0), 3, 150)
        
        records.append({
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
            "health_index": round(thi, 2),
            "health_status": "Critical",
            "primary_fault": fault_type,
            "rul_days": round(rul, 1)
        })
        
    df = pd.DataFrame(records)
    # Shuffle
    df = df.sample(frac=1.0, random_state=random_state).reset_index(drop=True)
    return df

if __name__ == "__main__":
    df = generate_transformer_dataset(4000)
    df.to_csv(config.DATASET_PATH, index=False)
    print(f"Dataset generated with {len(df)} samples at {config.DATASET_PATH}")
    print("\nClass distribution:")
    print(df["health_status"].value_counts(normalize=True) * 100)
    print("\nFeature Summary:")
    print(df[["winding_temperature", "oil_temperature", "vibration_rms", "load_current", "health_index"]].describe().round(2))
