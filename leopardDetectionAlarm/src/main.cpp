#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

const char* ssid = "monster13";
const char* password = "elizabethOlsen";
const char* serverURL = "http://10.176.218.163:3000/check-alarm";  // Fixed URL

const int LED_PIN = 5;      // g5 
const int BUZZER_PIN = 18;  // g18

// Real-time polling interval (ms) - small for near realtime checks
const unsigned long QUERY_INTERVAL = 5UL * 1000UL;  // 5 seconds

// After receiving a TRUE alarm from server, DO NOT query backend for this many ms:
const unsigned long SUPPRESS_AFTER_ALARM_MS = 5UL * 60UL * 1000UL; // 5 minutes

// How long the local alarm (LED + buzzer) runs each trigger
const unsigned long ALARM_DURATION = 15UL * 1000UL; // 15 seconds

// internals
unsigned long alarmStartTime = 0;
bool alarmActive = false;

// next time we're allowed to query the server (ms epoch)
unsigned long nextQueryTime = 0;

void connectToWiFi();
bool queryAlarmStatus();
void triggerAlarm();
void stopAlarm();

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);

  connectToWiFi();

  // start first query immediately
  nextQueryTime = 0;

  Serial.println("🚀 ESP32 Alarm System Started (LED + Buzzer Only)");
  Serial.print("Polling every (ms): ");
  Serial.println(QUERY_INTERVAL);
  Serial.print("Suppress after alarm (ms): ");
  Serial.println(SUPPRESS_AFTER_ALARM_MS);
}

void connectToWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.printf("📶 Connecting to WiFi: %s\n", ssid);
  WiFi.begin(ssid, password);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) { // ~30s max
    delay(1000);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ Connected to WiFi!");
    Serial.print("📡 IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n❌ WiFi connection failed!");
    Serial.print("📛 Failure reason: ");
    switch (WiFi.status()) {
      case WL_NO_SSID_AVAIL: Serial.println("Network not found"); break;
      case WL_CONNECT_FAILED: Serial.println("Password wrong?"); break;
      case WL_CONNECTION_LOST: Serial.println("Connection lost"); break;
      case WL_DISCONNECTED: Serial.println("Disconnected"); break;
      default: Serial.println("Unknown error"); break;
    }
  }
}

// returns true if server indicated an alarm (or provided a recent detection)
bool queryAlarmStatus() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("❌ WiFi not connected. Attempting reconnect...");
    connectToWiFi();
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("❌ Still offline - skipping this cycle.");
      return false;
    }
  }

  HTTPClient http;
  Serial.print("🔍 Querying: ");
  Serial.println(serverURL);

  http.begin(serverURL);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(10000); // 10s

  // small request body if you want to identify device
  DynamicJsonDocument reqDoc(256);
  reqDoc["device_id"] = "esp32_alarm_001";
  reqDoc["timestamp"] = millis();
  String requestBody;
  serializeJson(reqDoc, requestBody);

  int httpResponseCode = http.POST(requestBody);
  bool alarmStatus = false;

  Serial.print("📡 HTTP Response code: ");
  Serial.println(httpResponseCode);

  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.print("📥 Response: ");
    Serial.println(response);

    // parse JSON safely
    // allocate enough for expected response (alarm + detection object)
    DynamicJsonDocument respDoc(1024);
    DeserializationError err = deserializeJson(respDoc, response);

    if (!err) {
      Serial.println("✅ JSON parsed");

      // primary check: "alarm" boolean
      if (respDoc.containsKey("alarm")) {
        alarmStatus = respDoc["alarm"].as<bool>();
        Serial.print("🚨 alarm field: ");
        Serial.println(alarmStatus ? "true" : "false");
      }
      // secondary: presence of detection object (server returns detection details)
      else if (respDoc.containsKey("detection")) {
        // We consider detection = present => treat as alarm true
        alarmStatus = true;
        Serial.println("🚨 detection object present => alarm true");
      }
      // fallback: some servers might use other keys - check success + detection
      else if (respDoc.containsKey("success") && respDoc.containsKey("detection")) {
        alarmStatus = respDoc["detection"].is<JsonObject>();
      } else {
        Serial.println("ℹ️ No 'alarm' or 'detection' keys in response.");
        // for debugging print available keys
        Serial.println("Available keys:");
        for (JsonPair kv : respDoc.as<JsonObject>()) {
          Serial.print(" - ");
          Serial.println(kv.key().c_str());
        }
      }
    } else {
      Serial.print("❌ JSON parse failed: ");
      Serial.println(err.c_str());
    }
  } else {
    Serial.print("❌ HTTP Error: ");
    Serial.println(httpResponseCode);
    Serial.print("📛 ");
    Serial.println(http.errorToString(httpResponseCode));
  }

  http.end();
  return alarmStatus;
}

void triggerAlarm() {
  if (!alarmActive) {
    Serial.println("🚨🚨🚨 ALARM TRIGGERED! (local LED + buzzer) 🚨🚨🚨");
  } else {
    Serial.println("🚨 Alarm retriggered (already active) - extending or restarting local alarm.");
  }
  alarmActive = true;
  alarmStartTime = millis();
  // activate outputs
  digitalWrite(LED_PIN, HIGH);
  digitalWrite(BUZZER_PIN, HIGH);

  // Suppress further backend requests for SUPPRESS_AFTER_ALARM_MS
  nextQueryTime = millis() + SUPPRESS_AFTER_ALARM_MS;
  Serial.print("⏳ Suppressing backend queries until (ms epoch): ");
  Serial.println(nextQueryTime);
}

void stopAlarm() {
  if (alarmActive) Serial.println("🛑 Alarm stopped (duration expired)");
  alarmActive = false;
  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);
}

void loop() {
  unsigned long now = millis();

  // local alarm blinking logic and stop after ALARM_DURATION
  if (alarmActive) {
    // simple blink: 500ms on/off
    if ((now - alarmStartTime) % 1000 < 500) {
      digitalWrite(LED_PIN, HIGH);
    } else {
      digitalWrite(LED_PIN, LOW);
    }

    if (now - alarmStartTime >= ALARM_DURATION) {
      stopAlarm();
    }
  }

  // Only query backend if we're past nextQueryTime
  if (now >= nextQueryTime) {
    Serial.println("⏰ Time to check server now.");
    bool serverSaysAlarm = queryAlarmStatus();
    // schedule next regular query in normal interval unless query returned alarm,
    // in which case triggerAlarm() sets nextQueryTime = now + SUPPRESS_AFTER_ALARM_MS
    if (serverSaysAlarm) {
      triggerAlarm();
      // triggerAlarm() already set nextQueryTime to suppression window
    } else {
      // schedule next check
      nextQueryTime = now + QUERY_INTERVAL;
      Serial.print("✅ No alarm from server. Next check at (ms epoch): ");
      Serial.println(nextQueryTime);
    }
  } else {
    // nextQueryTime in future - optionally print a concise status occasionally
    static unsigned long lastStatus = 0;
    if (now - lastStatus >= 15000) { // log every 15s to avoid spam
      long sLeft = (long)(nextQueryTime - now) / 1000;
      if (sLeft < 0) sLeft = 0;
      Serial.print("⏱ Next server check in ");
      Serial.print(sLeft);
      Serial.println("s");
      lastStatus = now;
    }
  }

  // small delay to keep CPU low and allow WiFi background tasks
  delay(100);
}
