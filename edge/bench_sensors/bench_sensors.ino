#include <Wire.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <DHT.h>
#include <math.h>
#if __has_include("wifi_config.h")
#include "wifi_config.h"
#include <WiFi.h>
#include <HTTPClient.h>

String jsonNumber(float value) {
  return isfinite(value) ? String(value, 4) : String("null");
}
#endif

// ---------- ESP32 connections ----------
constexpr int TEMP_PIN = 4;
constexpr int DHT_PIN = 27;
constexpr int CURRENT_PIN = 34;
constexpr int VOLTAGE_PIN = 35;

// ---------- Sensors ----------
OneWire oneWire(TEMP_PIN);
DallasTemperature probes(&oneWire);
Adafruit_MPU6050 mpu;
DHT dht(DHT_PIN, DHT11);

// Your two previously detected probe addresses.
DeviceAddress probe1 = {
  0x28, 0x4A, 0x05, 0x56, 0xB5, 0x01, 0x3C, 0xF7
};

DeviceAddress probe2 = {
  0x28, 0xCA, 0x34, 0x56, 0xB5, 0x01, 0x3C, 0x54
};

bool mpuOK = false;
float latestAcceleration[3] = {NAN, NAN, NAN};

// ---------- Analog measurement settings ----------

// Your voltage board: 30k/7.5k, followed by an
// ADDITIONAL 10k/10k divider.
// Includes resistor loading; nominal factor = 13.
constexpr float VOLTAGE_FACTOR = 13.0f;

// ACS712 5A nominal sensitivity = 0.185 V/A.
// External 10k/10k divider halves it.
constexpr float CURRENT_SENSITIVITY = 0.0925f;

// Change to -1 if verified positive load current reads negative.
constexpr float CURRENT_DIRECTION = 1.0f;

// Leave at 1 until checked against a multimeter.
constexpr float VOLTAGE_CALIBRATION = 1.0f;

float currentZeroV = 0;

// ---------- Vibration settings ----------
// Approximately one-second windows at a target 250 samples/s.
constexpr int VIBRATION_SAMPLES = 250;
constexpr uint32_t SAMPLE_INTERVAL_US = 4000;

// DHT readings remain unverified.
float airC = NAN;
float humidity = NAN;
unsigned long lastDhtMs = 0;

// ---------- Helper functions ----------

float averageVolts(int pin, int samples = 100) {
  analogReadMilliVolts(pin);  // Discard after channel selection.
  delay(2);

  double total = 0;

  for (int i = 0; i < samples; i++) {
    total += analogReadMilliVolts(pin);
    delay(1);
  }

  return (total / samples) / 1000.0;
}

bool calibrateCurrent() {
  Serial.println();
  Serial.println("CURRENT ZERO CALIBRATION");
  Serial.println("Motor adapter must be UNPLUGGED.");
  Serial.println("Keep the motor OFF.");
  delay(3000);

  float candidate = averageVolts(CURRENT_PIN, 2000);

  Serial.print("Current zero at GPIO34: ");
  Serial.print(candidate, 4);
  Serial.println(" V");

  // Broad wiring sanity check, not an accuracy test.
  if (candidate < 1.0f || candidate > 1.5f) {
    Serial.println("Unexpected baseline. Check ACS712 power/divider.");
    return false;
  }

  currentZeroV = candidate;
  Serial.println("Zero baseline stored.");
  return true;
}

void printTemperature(const char *label,
                      const uint8_t *address) {
  float value = probes.getTempC(address);

  Serial.print(label);

  if (value == DEVICE_DISCONNECTED_C) {
    Serial.println("DISCONNECTED");
  } else {
    Serial.print(value, 2);
    Serial.println(" C");
  }
}

// RMS of acceleration variations about each window's mean.
// This removes constant gravity/offset for a stationary mounting.
// Movement or tilting the whole assembly also affects this metric.
void measureVibration(float &rms, float &sampleRate,
                      int &timingResets) {
  double mean[3] = {0, 0, 0};
  double m2[3] = {0, 0, 0};

  timingResets = 0;
  uint32_t nextSample = micros();
  uint32_t firstSample = 0;
  uint32_t lastSample = 0;

  for (int n = 1; n <= VIBRATION_SAMPLES; n++) {
    while ((int32_t)(micros() - nextSample) < 0) {
      delayMicroseconds(20);
    }

    uint32_t sampleTime = micros();
    if (n == 1) firstSample = sampleTime;
    lastSample = sampleTime;

    sensors_event_t a, g, t;
    mpu.getEvent(&a, &g, &t);

    double values[3] = {
      a.acceleration.x,
      a.acceleration.y,
      a.acceleration.z
    };

    // Numerically stable running variance.
    for (int axis = 0; axis < 3; axis++) {
      latestAcceleration[axis] = values[axis];
      double difference = values[axis] - mean[axis];
      mean[axis] += difference / n;
      m2[axis] += difference * (values[axis] - mean[axis]);
    }

    nextSample += SAMPLE_INTERVAL_US;

    // Avoid rapid catch-up samples if a deadline was missed.
    if ((int32_t)(micros() - nextSample) >= 0) {
      timingResets++;
      nextSample = micros() + SAMPLE_INTERVAL_US;
    }
  }

  double varianceSum =
      (m2[0] + m2[1] + m2[2]) / VIBRATION_SAMPLES;

  if (varianceSum < 0) varianceSum = 0;
  rms = sqrt(varianceSum);

  uint32_t elapsed = lastSample - firstSample;
  sampleRate = elapsed > 0
      ? (VIBRATION_SAMPLES - 1) * 1000000.0f / elapsed
      : 0;
}

void scanTemperatureProbes() {
  DeviceAddress address;
  unsigned int count = 0;
  Serial.printf("GPIO4 idle: %s\n", digitalRead(TEMP_PIN) ? "HIGH" : "LOW");
  Serial.printf("OneWire presence: %s\n", oneWire.reset() ? "YES" : "NO");
  oneWire.reset_search();
  while (oneWire.search(address)) {
    if (address[0] != 0x28 || OneWire::crc8(address, 7) != address[7]) continue;
    count++;
    Serial.print("DS18B20 ");
    for (int i = 0; i < 8; i++) Serial.printf("%02X", (unsigned int)address[i]);
    Serial.print(" ");
    probes.requestTemperaturesByAddress(address);
    delay(800);
    printTemperature("Measured temperature: ", address);
  }
  oneWire.reset_search();
  Serial.printf("GPIO4 probes found: %u\n", count);
}

void setup() {
#ifdef MACHGUARD_WIFI_SSID
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(MACHGUARD_WIFI_SSID, MACHGUARD_WIFI_PASSWORD);
#endif
  Serial.begin(115200);
  delay(1500);

  Serial.println("\n=== MachGuard monitoring-only prototype ===");
  Serial.println("No motor driver or motor-control outputs.");
  Serial.println("Keep motor adapter UNPLUGGED during setup.");

  analogReadResolution(12);
  analogSetPinAttenuation(CURRENT_PIN, ADC_11db);
  analogSetPinAttenuation(VOLTAGE_PIN, ADC_11db);

  probes.begin();
  probes.setResolution(12);
  probes.setWaitForConversion(false);
  scanTemperatureProbes();

  Serial.print("Temperature probe 1: ");
  Serial.println(probes.isConnected(probe1) ? "FOUND" : "MISSING");

  Serial.print("Temperature probe 2: ");
  Serial.println(probes.isConnected(probe2) ? "FOUND" : "MISSING");

  dht.begin();

  Wire.begin(21, 22);
  Wire.setClock(400000);

  mpuOK = mpu.begin(0x68);

  if (mpuOK) {
    mpu.setAccelerometerRange(MPU6050_RANGE_4_G);
    mpu.setGyroRange(MPU6050_RANGE_500_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_94_HZ);
    mpu.setSampleRateDivisor(3);  // 1kHz / (1 + 3) = 250Hz
    Serial.println("MPU6050 FOUND");
  } else {
    Serial.println("MPU6050 MISSING: check wiring");
  }

  Serial.println("Allowing analog supply to settle...");
  delay(5000);

  if (!calibrateCurrent()) {
    Serial.println("Stopped: correct wiring, then press RESET.");
    while (true) {
      delay(1000);
    }
  }

  probes.requestTemperatures();
  delay(800);

  Serial.println();
  Serial.println("READY: startup calibration finished.");
  Serial.println("You may now power the secured motor.");
  Serial.println("Unplug adapter to stop the motor.");
  Serial.println("Send c ONLY with motor adapter unplugged");
  Serial.println("to recalibrate the current baseline.");
}

void loop() {
  if (Serial.available()) {
    char command = Serial.read();

    if (command == 'c' || command == 'C') {
      // User must unplug motor power before sending this.
      calibrateCurrent();
    }
  }

  // Start both temperature conversions together.
  probes.requestTemperatures();
  unsigned long conversionStart = millis();

  float vibrationRms = NAN;
  float actualSampleRate = 0;
  int timingResets = 0;

  if (mpuOK) {
    measureVibration(vibrationRms, actualSampleRate, timingResets);
  } else {
    delay(1000);
  }

  // Ensure DS18B20 conversions have completed.
  while (millis() - conversionStart < 800) {
    delay(1);
  }

  // Analog readings occur outside the vibration sampling window.
  float currentAdcV = averageVolts(CURRENT_PIN, 200);
  float voltageAdcV = averageVolts(VOLTAGE_PIN, 200);

  float currentA =
      CURRENT_DIRECTION *
      (currentAdcV - currentZeroV) / CURRENT_SENSITIVITY;

  float motorVoltage =
      voltageAdcV * VOLTAGE_FACTOR * VOLTAGE_CALIBRATION;

  if (millis() - lastDhtMs >= 2500) {
    airC = dht.readTemperature();
    humidity = dht.readHumidity();
    lastDhtMs = millis();
  }

  Serial.println("\n--- MachGuard readings ---");
  Serial.print("Uptime: ");
  Serial.print(millis() / 1000);
  Serial.println(" seconds");

  printTemperature("Surface temperature 1: ", probe1);
  printTemperature("Surface temperature 2: ", probe2);

  Serial.print("Current ADC voltage: ");
  Serial.print(currentAdcV, 4);
  Serial.println(" V");

  Serial.print("Estimated motor current [uncalibrated]: ");
  Serial.print(currentA, 3);
  Serial.println(" A");

  Serial.print("Voltage ADC voltage: ");
  Serial.print(voltageAdcV, 4);
  Serial.println(" V");

  Serial.print("Motor terminal voltage [uncalibrated]: ");
  Serial.print(motorVoltage, 2);
  Serial.println(" V");

  if (mpuOK) {
    Serial.print("Acceleration variation RMS: ");
    Serial.print(vibrationRms, 4);
    Serial.println(" m/s^2");

    Serial.print("Measured sample rate: ");
    Serial.print(actualSampleRate, 1);
    Serial.println(" Hz");

    Serial.print("Sampling timing resets: ");
    Serial.println(timingResets);
  } else {
    Serial.println("Vibration: unavailable");
  }

  if (isnan(airC) || isnan(humidity)) {
    Serial.println("DHT11 [UNVERIFIED]: reading unavailable");
  } else {
    Serial.print("DHT11 temperature [UNVERIFIED]: ");
    Serial.print(airC, 1);
    Serial.println(" C");

    Serial.print("DHT11 humidity [UNVERIFIED]: ");
    Serial.print(humidity, 1);
    Serial.println(" %");
  }

#ifdef MACHGUARD_WIFI_SSID
  if (WiFi.status() == WL_CONNECTED) {
    float first = probes.getTempC(probe1);
    float second = probes.getTempC(probe2);
    String body = "{";
    body += "\"probe_c\":" + jsonNumber(first == DEVICE_DISCONNECTED_C ? NAN : first);
    body += ",\"probe2_c\":" + jsonNumber(second == DEVICE_DISCONNECTED_C ? NAN : second);
    body += ",\"air_c\":" + jsonNumber(airC);
    body += ",\"humidity_pct\":" + jsonNumber(humidity);
    body += ",\"current_a\":" + jsonNumber(currentA);
    body += ",\"current_adc_v\":" + jsonNumber(currentAdcV);
    body += ",\"motor_v\":" + jsonNumber(motorVoltage);
    body += ",\"voltage_adc_v\":" + jsonNumber(voltageAdcV);
    body += ",\"vibration_rms\":" + jsonNumber(vibrationRms);
    body += ",\"sample_hz\":" + jsonNumber(mpuOK ? actualSampleRate : NAN);
    body += ",\"ax\":" + jsonNumber(latestAcceleration[0]);
    body += ",\"ay\":" + jsonNumber(latestAcceleration[1]);
    body += ",\"az\":" + jsonNumber(latestAcceleration[2]);
    if (mpuOK) body += ",\"timing_resets\":" + String(timingResets);
    body += ",\"uptime_s\":" + String(millis() / 1000) + "}";
    WiFiClient client;
    HTTPClient http;
    http.setConnectTimeout(1500);
    http.setTimeout(2000);
    if (http.begin(client, MACHGUARD_SAMPLE_URL)) {
      http.addHeader("Content-Type", "application/json");
      http.addHeader("X-Device-Key", MACHGUARD_DEVICE_KEY);
      Serial.printf("Wi-Fi upload HTTP %d\n", http.POST(body));
      http.end();
    }
  } else {
    Serial.println("Wi-Fi disconnected");
  }
#endif
  delay(300);
}
