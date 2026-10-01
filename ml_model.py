"""
AI/ML Health Prediction Inference Engine for Transformers
Provides real-time health scoring, classification, fault diagnosis, and RUL estimation.
"""

import os
import joblib
import pandas as pd
import numpy as np
import config

class TransformerHealthPredictor:
    def __init__(self):
        self.model_bundle = None
        self.load_or_train()

    def load_or_train(self):
        """Load trained model or invoke training if absent."""
        if os.path.exists(config.MODEL_PATH):
            try:
                self.model_bundle = joblib.load(config.MODEL_PATH)
                return
            except Exception as e:
                print(f"Error loading model: {e}. Re-training...")
        
        from train_model import train_and_save_models
        self.model_bundle = train_and_save_models()

    def _prepare_features(self, sensor_dict: dict) -> pd.DataFrame:
        """Calculate base and derived features matching training schema."""
        row = {
            "oil_temperature": float(sensor_dict.get("oil_temperature", 50.0)),
            "winding_temperature": float(sensor_dict.get("winding_temperature", 60.0)),
            "ambient_temperature": float(sensor_dict.get("ambient_temperature", 28.0)),
            "ambient_humidity": float(sensor_dict.get("ambient_humidity", 50.0)),
            "vibration_rms": float(sensor_dict.get("vibration_rms", 0.25)),
            "load_current": float(sensor_dict.get("load_current", 60.0)),
            "voltage": float(sensor_dict.get("voltage", 230.0)),
            "oil_level": float(sensor_dict.get("oil_level", 88.0)),
            "gas_ppm": float(sensor_dict.get("gas_ppm", 250.0)),
        }
        # Derived features
        row["temp_gradient"] = row["winding_temperature"] - row["oil_temperature"]
        row["oil_rise"] = row["oil_temperature"] - row["ambient_temperature"]
        row["apparent_power"] = (row["voltage"] * row["load_current"]) / 1000.0

        df = pd.DataFrame([row])
        feature_cols = self.model_bundle["feature_cols"]
        return df[feature_cols]

    def _diagnose_faults(self, sensor_dict: dict) -> tuple[str, list[str]]:
        """Identify physical fault root-causes based on IEEE/IEC thresholds."""
        faults = []
        w_temp = float(sensor_dict.get("winding_temperature", 60.0))
        o_temp = float(sensor_dict.get("oil_temperature", 50.0))
        vib = float(sensor_dict.get("vibration_rms", 0.25))
        curr = float(sensor_dict.get("load_current", 60.0))
        gas = float(sensor_dict.get("gas_ppm", 250.0))
        oil_lvl = float(sensor_dict.get("oil_level", 88.0))
        hum = float(sensor_dict.get("ambient_humidity", 50.0))
        volt = float(sensor_dict.get("voltage", 230.0))

        if w_temp > config.THRESHOLDS["winding_temperature"]["critical_max"]:
            faults.append(f"Critical Winding Overheating ({w_temp:.1f}°C > {config.THRESHOLDS['winding_temperature']['critical_max']}°C)")
        elif w_temp > config.THRESHOLDS["winding_temperature"]["warning_max"]:
            faults.append(f"Elevated Winding Temperature ({w_temp:.1f}°C)")

        if o_temp > config.THRESHOLDS["oil_temperature"]["critical_max"]:
            faults.append(f"Severe Oil Overheating ({o_temp:.1f}°C)")
        elif o_temp > config.THRESHOLDS["oil_temperature"]["warning_max"]:
            faults.append(f"Elevated Oil Temperature ({o_temp:.1f}°C)")

        if vib > config.THRESHOLDS["vibration_rms"]["critical_max"]:
            faults.append(f"Severe Mechanical Vibration ({vib:.2f}g - Core/Winding Looseness)")
        elif vib > config.THRESHOLDS["vibration_rms"]["warning_max"]:
            faults.append(f"Abnormal Vibration Detected ({vib:.2f}g)")

        if curr > config.THRESHOLDS["load_current"]["critical_max"]:
            faults.append(f"Severe Current Overload ({curr:.1f}A)")
        elif curr > config.THRESHOLDS["load_current"]["warning_max"]:
            faults.append(f"Load Overcurrent Warning ({curr:.1f}A)")

        if gas > config.THRESHOLDS["gas_ppm"]["critical_max"]:
            faults.append(f"Critical Dissolved Gas TDCG ({gas:.0f} ppm - Arcing/Corona)")
        elif gas > config.THRESHOLDS["gas_ppm"]["warning_max"]:
            faults.append(f"Elevated Combustible Gas TDCG ({gas:.0f} ppm)")

        if oil_lvl < config.THRESHOLDS["oil_level"]["critical_min"]:
            faults.append(f"Critical Low Transformer Oil ({oil_lvl:.1f}%)")
        elif oil_lvl < config.THRESHOLDS["oil_level"]["warning_min"]:
            faults.append(f"Low Transformer Oil Level ({oil_lvl:.1f}%)")

        if hum > config.THRESHOLDS["ambient_humidity"]["warning_max"]:
            faults.append(f"High Ambient Humidity ({hum:.1f}% - Moisture Risk)")

        if volt < config.THRESHOLDS["voltage"]["min"] or volt > config.THRESHOLDS["voltage"]["max"]:
            faults.append(f"Voltage Deviation ({volt:.1f}V)")

        primary = faults[0] if faults else "None (Healthy)"
        return primary, faults

    def predict(self, sensor_dict: dict) -> dict:
        """Run ML prediction pipeline on live sensor data."""
        if self.model_bundle is None:
            self.load_or_train()

        X = self._prepare_features(sensor_dict)
        
        clf = self.model_bundle["classifier"]
        reg = self.model_bundle["regressor"]
        rul_model = self.model_bundle["rul_model"]

        # Health status and confidence
        status_pred = clf.predict(X)[0]
        status_probs = clf.predict_proba(X)[0]
        class_idx = list(clf.classes_).index(status_pred)
        confidence = float(status_probs[class_idx])

        # Health index score (0-100)
        health_index = float(np.clip(reg.predict(X)[0], 0.0, 100.0))

        # RUL days
        rul_days = float(np.clip(rul_model.predict(X)[0], 1.0, 3650.0))

        # Root-cause diagnostic
        primary_fault, fault_causes = self._diagnose_faults(sensor_dict)

        # Anomaly detection: flag if non-normal or severe causes present
        is_anomaly = (status_pred in ["Warning", "Critical"]) or (len(fault_causes) > 0)

        # Ensure consistency: if severe fault detected by rules, status shouldn't be Normal
        if len(fault_causes) >= 2 and status_pred == "Normal":
            status_pred = "Warning"
            health_index = min(health_index, 75.0)

        return {
            "health_index": round(health_index, 2),
            "health_status": status_pred,
            "confidence": round(confidence, 3),
            "rul_days": round(rul_days, 1),
            "anomaly_detected": is_anomaly,
            "primary_fault": primary_fault,
            "fault_causes": fault_causes,
            "feature_importances": self.model_bundle.get("feature_importances", {})
        }

# Global singleton
_predictor = None

def get_predictor() -> TransformerHealthPredictor:
    global _predictor
    if _predictor is None:
        _predictor = TransformerHealthPredictor()
    return _predictor
