"""
Model Training Pipeline for IoT Transformer Health Prediction
Trains Classifier (Health Status), Regressor (Health Index), and RUL Predictor.
"""

import os
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import classification_report, accuracy_score, r2_score, mean_absolute_error

import config
from generate_dataset import generate_transformer_dataset

FEATURE_COLS = [
    "oil_temperature",
    "winding_temperature",
    "ambient_temperature",
    "ambient_humidity",
    "vibration_rms",
    "load_current",
    "voltage",
    "oil_level",
    "gas_ppm",
    "temp_gradient",
    "oil_rise",
    "apparent_power"
]

def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add engineering domain features for transformers."""
    data = df.copy()
    data["temp_gradient"] = data["winding_temperature"] - data["oil_temperature"]
    data["oil_rise"] = data["oil_temperature"] - data["ambient_temperature"]
    data["apparent_power"] = (data["voltage"] * data["load_current"]) / 1000.0  # kVA
    return data

def train_and_save_models():
    """Execute training pipeline and save artifacts."""
    os.makedirs(config.MODELS_DIR, exist_ok=True)
    
    # 1. Dataset loading / generation
    if not os.path.exists(config.DATASET_PATH):
        print("Dataset not found. Generating 4000 synthetic samples...")
        df = generate_transformer_dataset(4000)
        df.to_csv(config.DATASET_PATH, index=False)
    else:
        print(f"Loading dataset from {config.DATASET_PATH}...")
        df = pd.read_csv(config.DATASET_PATH)
        
    df_feat = add_derived_features(df)
    X = df_feat[FEATURE_COLS]
    y_class = df_feat["health_status"]
    y_reg = df_feat["health_index"]
    y_rul = df_feat["rul_days"]
    
    X_train, X_test, y_class_train, y_class_test, y_reg_train, y_reg_test, y_rul_train, y_rul_test = train_test_split(
        X, y_class, y_reg, y_rul, test_size=0.20, random_state=42, stratify=y_class
    )
    
    print("\n" + "="*50)
    print("1. Training Random Forest Classifier (Health Status)...")
    clf = RandomForestClassifier(n_estimators=120, max_depth=14, min_samples_split=4, random_state=42, n_jobs=-1)
    clf.fit(X_train, y_class_train)
    y_pred_class = clf.predict(X_test)
    acc = accuracy_score(y_class_test, y_pred_class)
    print(f"Classifier Accuracy: {acc*100:.2f}%")
    print("\nClassification Report:")
    print(classification_report(y_class_test, y_pred_class))
    
    print("="*50)
    print("2. Training Random Forest Regressor (Health Index)...")
    reg = RandomForestRegressor(n_estimators=100, max_depth=14, min_samples_split=4, random_state=42, n_jobs=-1)
    reg.fit(X_train, y_reg_train)
    y_pred_reg = reg.predict(X_test)
    r2 = r2_score(y_reg_test, y_pred_reg)
    mae = mean_absolute_error(y_reg_test, y_pred_reg)
    print(f"Health Index Regressor R² Score: {r2:.4f}, MAE: {mae:.2f} points")
    
    print("="*50)
    print("3. Training Gradient Boosting Regressor (RUL - Remaining Useful Life)...")
    rul_model = GradientBoostingRegressor(n_estimators=100, max_depth=5, learning_rate=0.08, random_state=42)
    rul_model.fit(X_train, y_rul_train)
    y_pred_rul = rul_model.predict(X_test)
    rul_mae = mean_absolute_error(y_rul_test, y_pred_rul)
    print(f"RUL Model MAE: {rul_mae:.2f} days")
    
    # Feature importances
    importances = dict(zip(FEATURE_COLS, clf.feature_importances_))
    sorted_importances = dict(sorted(importances.items(), key=lambda item: item[1], reverse=True))
    print("\nTop Feature Importances (Classifier):")
    for feat, imp in list(sorted_importances.items())[:6]:
        print(f"  {feat:<22}: {imp*100:.2f}%")
        
    model_bundle = {
        "classifier": clf,
        "regressor": reg,
        "rul_model": rul_model,
        "feature_cols": FEATURE_COLS,
        "feature_importances": sorted_importances,
        "metrics": {
            "accuracy": acc,
            "r2_score": r2,
            "mae": mae,
            "rul_mae": rul_mae
        }
    }
    
    joblib.dump(model_bundle, config.MODEL_PATH)
    print("="*50)
    print(f"Saved complete model bundle to {config.MODEL_PATH}")
    return model_bundle

if __name__ == "__main__":
    train_and_save_models()
