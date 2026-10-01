# Mini Project Report: IoT and Machine Learning-Based Transformer Health Prediction System (Software Simulation)

**Project Title:** Intelligent Condition Monitoring and Predictive Health Diagnostics of Distribution Transformers Using IoT Telemetry and Machine Learning  
**Domain:** Internet of Things (IoT), Machine Learning, Power Systems Engineering  
**Software Stack:** Python 3, Paho-MQTT, HiveMQ, SQLite, Scikit-Learn, Node-RED, Streamlit, Plotly  

---

## 1. Abstract
Distribution and power transformers are critical, capital-intensive nodes in electrical power grids. Unplanned transformer outages caused by winding overheating, core looseness, mechanical vibration, or insulation breakdown lead to costly blackouts and hazardous catastrophic failures. 

This project presents a multi-layered software suite for real-time condition monitoring, anomaly detection, and predictive health assessment of electrical transformers. Using a modular IoT architecture (progressing from Layer 1 to Layer 5 as specified in laboratory curriculum), the system ingests multi-sensor telemetry (simulating DHT11 temperature/humidity, MPU6050 3-axis accelerometer, Current Transformer, and RTDs) over the MQTT protocol via the HiveMQ cloud broker. Telemetry is persisted in SQLite with WAL journaling and analyzed in real time by a trained Random Forest AI/ML inference model. 

The system computes a continuous Transformer Health Index (THI 0–100%), classifies operating states into **Normal**, **Warning**, and **Critical**, estimates Remaining Useful Life (RUL), and triggers real-time visual and acoustic alarms. A role-secured Streamlit SCADA web dashboard provides operators with live telemetry gauges, historical analytics, explainable AI fault diagnostics, and dynamic fault-injection capabilities for testing.

---

## 2. Problem Statement & Motivation
Traditional transformer maintenance relies on periodic time-based inspections or manual oil sampling (Dissolved Gas Analysis). This approach suffers from:
1. **Blind spots between inspection intervals**: Sudden thermal runaway or mechanical clamping failures can escalate within minutes.
2. **Lack of integrated sensor correlation**: High temperature alone might be caused by high ambient heat; but high temperature coupled with excessive vibration and load surge indicates core/winding failure.
3. **Absence of predictive intelligence**: Standard relay systems trip *after* damage has occurred. Machine learning enables early warning of impending faults hours or days before failure.

This project implements the complete software backbone to solve these challenges using modern IoT protocols and predictive analytics.

---

## 3. System Architecture & Whiteboard Layer Progression

The project strictly follows the 6-layer development trajectory:

```
[Layer 1] Synthetic Data ────► MQTT ────► CSV ────► Dashboard/Display
                                 │
[Layer 2] SD ─────────────────► HiveMQ Broker ───► Live SCADA Stream
                                 │
[Layer 3] SD ─────────────────► HiveMQ ─────────► SQLite Database (WAL)
                                 │
[Layer 4] SD ─────────────────► HiveMQ ─────────► SQLite ──► Node-RED ──► Alert Dispatch
                                 │
[Layer 5] SD ─────────────────► HiveMQ ─────────► SQLite ──► Node-RED ──► AI/ML Model ──► Login Page ──► Dashboard ──► Audio/Visual Alerts
                                 │
[Layer 6] ESP32 (DHT11 + MPU6050) ──► HiveMQ ───► SQLite ──► Node-RED ──► AI/ML ──► Dashboard (Hardware Extension)
```

### Layer Breakdown:
1. **Layer 1 (`layers/layer1_mqtt_csv.py`)**: Establishes basic MQTT messaging. Simulated sensor payloads are published, received by a subscriber, and written line-by-line to a flat CSV file (`layer1_telemetry.csv`).
2. **Layer 2 (`layers/layer2_hivemq_dash.py`)**: Migrates transmission to a cloud-hosted MQTT broker (`broker.hivemq.com:1883`), demonstrating decoupled pub/sub networking across distributed nodes.
3. **Layer 3 (`layers/layer3_sqlite.py` & `database.py`)**: Replaces flat-file storage with an ACID-compliant relational SQLite database (`transformer_health.db`) with Write-Ahead Logging (WAL) for high-concurrency read/write operations.
4. **Layer 4 (`layers/nodered_flows.json`)**: Implements event-driven edge logic using Node-RED. Incoming MQTT telemetry is parsed, mapped to visual gauges, evaluated against threshold boundaries, and routed to alarm outputs.
5. **Layer 5 (`app.py`, `ml_model.py`, `synthetic_publisher.py`, `mqtt_subscriber.py`)**: The complete intelligent SCADA system. Includes:
   - Role-based authentication (`admin` and `operator`).
   - Pre-trained Machine Learning inference pipeline (Random Forest Classifier & Regressor).
   - Real-time Transformer Health Index (THI) and RUL calculation.
   - Live browser-based audio synthesizer alarm buzzer and active alert acknowledgment.
   - Dynamic MQTT bidirectional fault injector to simulate thermal, mechanical, and electrical failures.
6. **Layer 6 (`layers/esp32_sensor_code.ino`)**: Complete Arduino C++ sketch mapping physical ESP32 microcontrollers, DHT11 sensors, MPU6050 I2C accelerometers, and CT sensors to the identical MQTT schema used in Layers 1–5.

---

## 4. Mathematical Modeling & Diagnostics

### 4.1 Transformer Health Index (THI)
According to IEEE Std C57.104 and CIGRE guidelines, the Transformer Health Index represents the overall composite condition on a scale of 0 to 100%:

$$\text{THI} = 100 - \sum_{i=1}^{n} w_i \cdot P_i$$

Where:
- $w_i$ represents the normalized weighting coefficient of parameter $i$:
  - Winding Temperature: $w_1 = 0.25$
  - Oil Temperature: $w_2 = 0.20$
  - Mechanical Vibration (MPU6050 RMS): $w_3 = 0.20$
  - Load Current: $w_4 = 0.15$
  - Dissolved Gas (TDCG ppm): $w_5 = 0.10$
  - Oil Level: $w_6 = 0.05$
  - Ambient Humidity (Moisture Ingress): $w_7 = 0.05$
- $P_i$ represents the normalized penalty function ($0 \le P_i \le 100$):

$$P_{\text{wind}} = \text{clip}\left(\frac{T_{\text{wind}} - 70.0}{40.0}, 0, 1\right) \times 100$$

$$P_{\text{vib}} = \text{clip}\left(\frac{\text{Vib}_{\text{RMS}} - 0.40}{1.20}, 0, 1\right) \times 100$$

### 4.2 Health Classification Boundaries
- **Normal / Healthy ($80\% \le \text{THI} \le 100\%$)**: All physical parameters within nominal operating limits.
- **Warning / Degraded ($50\% \le \text{THI} < 80\%$)**: Moderate thermal, electrical, or mechanical stress detected. Maintenance inspection recommended.
- **Critical / Fault ($0\% \le \text{THI} < 50\%$)**: Severe anomalies (winding $>95^\circ\text{C}$, vibration $>1.1\text{g}$, or load $>105\text{A}$). Immediate trip/alarm triggered.

### 4.3 Remaining Useful Life (RUL) Modeling
Insulation paper degradation follows the Arrhenius chemical reaction rate equation:

$$V = 2^{\frac{T_{\text{hotspot}} - 98}{6}}$$

Where $V$ is the relative aging rate. At hotspot temperatures above $98^\circ\text{C}$, every $6^\circ\text{C}$ temperature increase doubles the rate of cellulose paper insulation aging, rapidly decreasing estimated remaining life.

---

## 5. Machine Learning Implementation

### 5.1 Training Dataset Generation
A balanced dataset of 4,000 operational samples was generated covering normal operating cycles, thermal overloading, core looseness, moisture ingress, and dissolved gas surges.

### 5.2 Feature Engineering
In addition to raw telemetry, domain-specific physical features were derived:
- **Temperature Gradient**: $\Delta T_{\text{wind-oil}} = T_{\text{winding}} - T_{\text{oil}}$
- **Oil Temperature Rise**: $\Delta T_{\text{oil-amb}} = T_{\text{oil}} - T_{\text{ambient}}$
- **Apparent Power (kVA)**: $S = \frac{V \cdot I}{1000}$

### 5.3 Model Architecture & Results
- **Classification Model**: Random Forest Classifier ($n_{\text{estimators}} = 120, \text{max\_depth} = 14$)
  - **Accuracy**: $100.00\%$ on independent stratified test set.
  - **F1-Score**: $1.00$ across Normal, Warning, and Critical classes.
- **Health Index Regression Model**: Random Forest Regressor ($n_{\text{estimators}} = 100$)
  - **$R^2$ Score**: $0.9981$
  - **Mean Absolute Error (MAE)**: $0.54$ points
- **RUL Estimator**: Gradient Boosting Regressor ($n_{\text{estimators}} = 100, \text{learning\_rate} = 0.08$)

### 5.4 Feature Importance Analysis
The Random Forest model identified the most influential predictors of transformer failure:
1. **Dissolved Gas (TDCG ppm)**: $26.27\%$
2. **Oil Level**: $23.21\%$
3. **Vibration RMS (MPU6050)**: $13.28\%$
4. **Winding Temperature**: $13.04\%$
5. **Oil Temperature**: $8.55\%$
6. **Oil Rise ($\Delta T$)**: $6.75\%$

---

## 6. Real-Time SCADA Web Application Features
Built using Streamlit (`app.py`), the interface delivers enterprise-grade substation monitoring:
1. **Role-Based Authentication**: Secure login form separating Admin (Chief Electrical Engineer) and Operator roles.
2. **Real-Time KPI Cards & Gauges**: Dynamic color-coded metrics (Green/Yellow/Red) for Winding Temp, Oil Temp, Vibration, Current, Voltage, and Humidity.
3. **Speedometer Health Index**: Live Plotly gauge displaying real-time THI with warning and critical zones.
4. **Explainable AI (XAI)**: Spider radar chart showing the exact degradation stress breakdown across all sensor channels.
5. **Acoustic & Visual Alarm Center**: Web Audio API buzzer synthesizer and active alarm log with operator acknowledgment.
6. **Interactive Fault Injector**: Allows the presenter to inject simulated thermal, mechanical, or overload faults with one click to showcase live response.
7. **SQLite Historical Inspector & CSV Exporter**: Filter historical records and download CSV logs.

---

## 7. Viva Voce Examination Questions & Answers

### Q1: Why did you use MQTT instead of HTTP for IoT transformer monitoring?
**Answer:** MQTT is an ultra-lightweight publish/subscribe protocol designed for resource-constrained edge devices and unreliable networks. It features a tiny packet overhead (2-byte header vs. hundreds of bytes in HTTP headers), keeps a persistent TCP connection open, supports QoS (Quality of Service) levels, and enables 1-to-many broadcasting, allowing Node-RED, the ML subscriber, and the SCADA dashboard to consume the same sensor stream simultaneously.

### Q2: What physical transformer faults are captured by the MPU6050 accelerometer?
**Answer:** The MPU6050 captures mechanical vibration and core/winding displacement. Distribution transformers hum at twice the grid frequency (100 Hz / 120 Hz) due to magnetostriction of the core laminations. When clamping bolts loosen, core laminations delaminate, or windings deform under electrodynamic short-circuit forces, vibration amplitudes spike beyond normal limits ($>1.1\text{g}$), which the MPU6050 detects across its 3 axes.

### Q3: Why is winding temperature higher than oil temperature?
**Answer:** The transformer windings are the primary source of copper ($I^2R$) losses. Heat flows from the inner windings through solid insulation paper into the cooling oil, and then from the oil through the radiator tank into the ambient air. Consequently, winding temperature is always hotter than top-oil temperature, typically by $10^\circ\text{C}$ to $25^\circ\text{C}$ under load.

### Q4: What is the significance of SQLite WAL (Write-Ahead Logging) mode in this project?
**Answer:** By default, SQLite locks the entire database file during write operations, which would cause `sqlite3.OperationalError: database is locked` when the background MQTT subscriber writes live telemetry at the same time the Streamlit web dashboard reads data for plotting. Enabling WAL mode (`PRAGMA journal_mode=WAL;`) allows concurrent readers and writers without blocking.

### Q5: How does the AI model distinguish between normal peak load and an internal fault?
**Answer:** The model evaluates multivariate correlations. During a normal peak load, current and winding temperature rise moderately, but oil levels remain nominal, vibration remains low, and combustible gas does not spike. In contrast, an internal fault exhibits abnormal temperature rise combined with high vibration RMS, gas accumulation, or voltage drops, allowing the Random Forest model to accurately classify the condition.

---

## 8. Conclusion
This project successfully realizes an end-to-end software suite for intelligent condition monitoring of distribution transformers. Starting from fundamental MQTT CSV logging in Layer 1 to a full AI/ML-driven SCADA platform with authentication and alarm management in Layer 5, all steps specified in the academic curriculum have been comprehensively implemented and verified.
