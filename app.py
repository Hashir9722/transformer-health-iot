"""
Transformer Health SCADA Dashboard
- Login page (users from config.USERS)
- Background thread publishes telemetry to HiveMQ every 2 s (independent of page refresh)
Run: streamlit run app.py
"""

import time
import json
import random
import threading
from collections import deque

import streamlit as st
import pandas as pd
import plotly.express as px
import paho.mqtt.client as mqtt

import config
from synthetic_publisher import generate_telemetry_reading
from ml_model import get_predictor

st.set_page_config(page_title="Transformer Health Monitor", page_icon="⚡", layout="wide")

MODES = ["NORMAL", "OVERHEATING", "VIBRATION_FAULT", "OVERLOAD", "LOW_OIL", "GAS_ARCING"]
PUBLISH_INTERVAL = 2.0


# ---------------------------------------------------------
# MQTT client (public broker: no username/password/TLS needed)
# ---------------------------------------------------------
def make_client(client_id):
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    except (AttributeError, TypeError):
        client = mqtt.Client(client_id=client_id)
    if config.MQTT_PORT == 8883:
        client.tls_set()
    user = getattr(config, "MQTT_USERNAME", "")
    if user:
        client.username_pw_set(user, getattr(config, "MQTT_PASSWORD", ""))
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    return client


# ---------------------------------------------------------
# Background engine: created ONCE, keeps publishing every 2 s
# ---------------------------------------------------------
@st.cache_resource
def get_engine():
    shared = {
        "mode": "NORMAL", "publish": True, "step": 0, "sent": 0,
        "connected": False, "info": "Connecting...",
        "history": deque(maxlen=60),
    }
    client = make_client(f"transformer_dash_{random.randint(1000, 9999)}")

    def on_connect(c, userdata, flags, rc, properties=None):
        shared["connected"] = (rc == 0)
        shared["info"] = f"Connected to {config.MQTT_BROKER}" if rc == 0 else f"Connect failed: {rc}"

    def on_disconnect(c, userdata, *args):
        shared["connected"] = False
        shared["info"] = "Disconnected - reconnecting..."

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect_async(config.MQTT_BROKER, config.MQTT_PORT, config.MQTT_KEEPALIVE)
    client.loop_start()

    predictor = get_predictor()

    def worker():
        next_t = time.monotonic()
        while True:
            try:
                shared["step"] += 1
                reading = generate_telemetry_reading(shared["step"], shared["mode"])
                pred = predictor.predict(reading)

                if shared["publish"] and shared["connected"]:
                    if client.publish(config.TOPIC_TELEMETRY, json.dumps(reading), qos=1).rc == 0:
                        shared["sent"] += 1
                    if pred["health_status"] in ("Warning", "Critical"):
                        client.publish(config.TOPIC_ALERTS, json.dumps({
                            "timestamp": reading["timestamp"],
                            "device_id": reading["device_id"],
                            "health_index": pred["health_index"],
                            "health_status": pred["health_status"],
                            "primary_fault": pred["primary_fault"],
                            "alerts": pred["fault_causes"]}), qos=1)

                shared["history"].append({
                    **reading,
                    "health_index": pred["health_index"],
                    "health_status": pred["health_status"],
                    "rul_days": pred["rul_days"],
                    "confidence": pred["confidence"],
                    "fault_causes": pred["fault_causes"],
                })
            except Exception as e:
                shared["info"] = f"Worker error: {e}"

            next_t += PUBLISH_INTERVAL              # fixed schedule, no drift
            time.sleep(max(0.0, next_t - time.monotonic()))

    threading.Thread(target=worker, daemon=True).start()
    return shared


# ---------------------------------------------------------
# Session state + login page
# ---------------------------------------------------------
for k, v in {"auth": False, "user": None, "role": None, "name": None}.items():
    st.session_state.setdefault(k, v)


def login_page():
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown("## ⚡ Transformer Health SCADA")
        st.caption("Sign in to continue")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
        if submitted:
            user = config.USERS.get(username.strip())
            if user and user["password"] == password:
                st.session_state.update(auth=True, user=username.strip(),
                                        role=user["role"], name=user["name"])
                st.rerun()
            else:
                st.error("Invalid username or password")


if not st.session_state.auth:
    login_page()
    st.stop()

# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------
engine = get_engine()
is_admin = st.session_state.role == "Administrator"
def set_mode():
    engine["mode"] = st.session_state["mode_sel"]

def set_publish():
    engine["publish"] = st.session_state["pub_sel"]

with st.sidebar:
    st.title("⚡ Control Panel")
    st.write(f"**{st.session_state.name}**")
    st.caption(f"Role: {st.session_state.role}")
    if st.button("Logout", use_container_width=True):
        for k in ("auth", "user", "role", "name"):
            st.session_state[k] = None if k != "auth" else False
        st.rerun()

    st.markdown("---")
    st.caption(f"{'🟢' if engine['connected'] else '🔴'} {engine['info']}")
    st.caption(f"Messages sent: **{engine['sent']}**")

    st.markdown("---")
    if is_admin:
                st.markdown("### 🧪 Fault Injector")
                st.session_state["mode_sel"] = engine["mode"]
                st.session_state["pub_sel"] = engine["publish"]
                st.selectbox("Simulation mode", MODES, key="mode_sel", on_change=set_mode)
                st.checkbox("Publish to HiveMQ", key="pub_sel", on_change=set_publish)
    else:
        st.info(f"Mode: **{engine['mode']}** (admin only)")

history = list(engine["history"])
if not history:
    st.info("Starting data stream...")
    time.sleep(1)
    st.rerun()

df = pd.DataFrame(history)
latest = history[-1]
hi, status = latest["health_index"], latest["health_status"]

st.title("⚡ Transformer Health Prediction Dashboard")
st.caption(f"Topic: `{config.TOPIC_TELEMETRY}` | Last update: `{latest['timestamp']}`")

c1, c2 = st.columns([3, 1.2])
with c1:
    if status == "Normal":
        st.success(f"### 🟢 NORMAL (Health Index {hi:.0f}%)")
    elif status == "Warning":
        st.warning(f"### 🟡 WARNING (Health Index {hi:.0f}%)")
    else:
        st.error(f"### 🔴 CRITICAL (Health Index {hi:.0f}%)")
    if latest["fault_causes"]:
        st.write("Issues: **" + ", ".join(latest["fault_causes"]) + "**")
with c2:
    st.metric("RUL (days)", f"{latest['rul_days']:.0f}",
              delta=f"Confidence {latest['confidence']*100:.0f}%")

tab_live, tab_log = st.tabs(["📊 Live Sensor Telemetry", "📜 Data Log & CSV"])

with tab_live:
    m = st.columns(5)
    m[0].metric("Winding °C", latest["winding_temperature"])
    m[1].metric("Oil °C", latest["oil_temperature"])
    m[2].metric("Vibration g", latest["vibration_rms"])
    m[3].metric("Current A", latest["load_current"])
    m[4].metric("Gas ppm", latest["gas_ppm"])

    T = config.THRESHOLDS

    def chart(y, title, warn=None, crit=None):
        fig = px.line(df, x="timestamp", y=y, title=title, markers=True)
        if warn:
            fig.add_hline(y=warn, line_dash="dash", line_color="orange")
        if crit:
            fig.add_hline(y=crit, line_dash="dash", line_color="red")
        st.plotly_chart(fig, use_container_width=True)

    a, b = st.columns(2)
    with a:
        chart("winding_temperature", "Winding Temperature (°C)",
              T["winding_temperature"]["warning_max"], T["winding_temperature"]["critical_max"])
        chart("load_current", "Load Current (A)",
              T["load_current"]["warning_max"], T["load_current"]["critical_max"])
    with b:
        chart("vibration_rms", "Vibration RMS (g)",
              T["vibration_rms"]["warning_max"], T["vibration_rms"]["critical_max"])
        chart("health_index", "Health Index (%)", 80, 50)

with tab_log:
    st.dataframe(df.drop(columns=["fault_causes"]), use_container_width=True)
    st.download_button("📥 Download CSV", df.drop(columns=["fault_causes"]).to_csv(index=False).encode(),
                       "transformer_telemetry.csv", "text/csv", use_container_width=True)

time.sleep(2)
st.rerun()