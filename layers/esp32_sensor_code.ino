/*
  =============================================================================
  LAYER 6 HARDWARE IMPLEMENTATION: ESP32 + DHT11 + MPU6050 + CT Sensor -> MQTT
  =============================================================================
  Whiteboard Specification:
  DHT11 & MPU6050 -> ESP32 -> MQTT -> HiveMQ -> SQLite -> Node-RED -> AI/ML -> Login -> Dashboard -> Alert + LED + Buzzer

  Hardware Pinout:
  - ESP32 GPIO 4  : DHT11 Data Pin (Ambient Temp & Humidity)
  - ESP32 GPIO 21 : MPU6050 SDA (I2C)
  - ESP32 GPIO 22 : MPU6050 SCL (I2C)
  - ESP32 GPIO 34 : Current Transformer (SCT-013 analog input)
  - ESP32 GPIO 35 : Oil Temperature (DS18B20 OneWire / Analog probe)
  - ESP32 GPIO 2  : Warning / Critical Status LED
  - ESP32 GPIO 15 : Alarm Buzzer (Active Low / High)
  =============================================================================
*/

#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <DHT.h>
#include <ArduinoJson.h>

// --- WiFi & MQTT Broker Credentials ---
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* mqtt_server = "broker.hivemq.com";
const int mqtt_port = 1883;

// Topic definitions matching the software project
const char* topic_telemetry = "transformer_health_iot_mini_proj_suhai/telemetry";
const char* topic_alerts    = "transformer_health_iot_mini_proj_suhai/alerts";

// --- Pin Definitions ---
#define DHTPIN 4
#define DHTTYPE DHT11
#define PIN_LED 2
#define PIN_BUZZER 15
#define PIN_CURRENT_ANALOG 34
#define PIN_OIL_TEMP_ANALOG 35

// --- Sensor Objects ---
DHT dht(DHTPIN, DHTTYPE);
Adafruit_MPU6050 mpu;
WiFiClient espClient;
PubSubClient client(espClient);

unsigned long lastMsg = 0;
const long interval = 2000; // 2 seconds telemetry period

void setup_wifi() {
  delay(10);
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected! IP address: ");
  Serial.println(WiFi.localIP());
}

void mqtt_callback(char* topic, byte* payload, unsigned int length) {
  // Listen for alert messages dispatched from Layer 4/5
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.print("[MQTT ALERT RECEIVED] ");
  Serial.println(message);

  // Turn on Hardware LED and Buzzer if alert triggers
  digitalWrite(PIN_LED, HIGH);
  digitalWrite(PIN_BUZZER, HIGH);
  delay(500);
  digitalWrite(PIN_BUZZER, LOW);
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting HiveMQ connection...");
    String clientId = "ESP32_Transformer_" + String(random(0xffff), HEX);
    if (client.connect(clientId.c_str())) {
      Serial.println("Connected to HiveMQ broker!");
      client.subscribe(topic_alerts);
    } else {
      Serial.print("Failed, rc=");
      Serial.print(client.state());
      Serial.println(" retrying in 5 seconds...");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_LED, LOW);
  digitalWrite(PIN_BUZZER, LOW);

  // Initialize DHT11
  dht.begin();

  // Initialize MPU6050
  Wire.begin(21, 22);
  if (!mpu.begin()) {
    Serial.println("Could not find a valid MPU6050 sensor, check wiring!");
  } else {
    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
    Serial.println("MPU6050 Initialized.");
  }

  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(mqtt_callback);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  unsigned long now = millis();
  if (now - lastMsg > interval) {
    lastMsg = now;

    // 1. Read DHT11
    float amb_hum = dht.readHumidity();
    float amb_temp = dht.readTemperature();
    if (isnan(amb_hum) || isnan(amb_temp)) {
      amb_hum = 55.0;
      amb_temp = 28.5;
    }

    // 2. Read MPU6050
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);
    // Convert m/s^2 to g-force
    float vib_x = a.acceleration.x / 9.80665;
    float vib_y = a.acceleration.y / 9.80665;
    float vib_z = a.acceleration.z / 9.80665;
    float vib_rms = sqrt(vib_x * vib_x + vib_y * vib_y + vib_z * vib_z);

    // 3. Read Analog Sensors (CT & Oil Temperature Probe)
    int raw_current = analogRead(PIN_CURRENT_ANALOG);
    float load_current = map(raw_current, 0, 4095, 20, 120);

    int raw_oil = analogRead(PIN_OIL_TEMP_ANALOG);
    float oil_temperature = map(raw_oil, 0, 4095, 30, 95);
    float winding_temperature = oil_temperature + 12.0 + (load_current / 10.0);

    // 4. Construct JSON Payload matching Layer 1-5 Schema
    StaticJsonDocument<350> doc;
    doc["timestamp"] = "ESP32-LIVE-STREAM";
    doc["device_id"] = "TRANSFORMER-ESP32-HW";
    doc["oil_temperature"] = oil_temperature;
    doc["winding_temperature"] = winding_temperature;
    doc["ambient_temperature"] = amb_temp;
    doc["ambient_humidity"] = amb_hum;
    doc["vibration_x"] = vib_x;
    doc["vibration_y"] = vib_y;
    doc["vibration_z"] = vib_z;
    doc["vibration_rms"] = vib_rms;
    doc["load_current"] = load_current;
    doc["voltage"] = 230.0;
    doc["oil_level"] = 87.0;
    doc["gas_ppm"] = 240.0;
    doc["fault_mode"] = "HARDWARE_ESP32";

    char buffer[400];
    serializeJson(doc, buffer);

    // Publish to HiveMQ topic
    client.publish(topic_telemetry, buffer);
    Serial.print("[PUBLISHED] ");
    Serial.println(buffer);
  }
}
