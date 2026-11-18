#include <Wire.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Adafruit_MPU6050.h>
#include <DHT.h>

OneWire bus(4);
DallasTemperature probe(&bus);
Adafruit_MPU6050 imu;
DHT air(27, DHT11);
bool imuReady;

void field(const char* name, float value, bool comma) {
  if (comma) Serial.print(',');
  Serial.printf("\"%s\":", name);
  if (isfinite(value)) Serial.print(value, 3);
  else Serial.print("null");
}

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);
  probe.begin();
  air.begin();
  imuReady = imu.begin();
}

void loop() {
  probe.requestTemperatures();
  float surface = probe.getTempCByIndex(0);
  sensors_event_t accel, gyro, temp;
  bool ok = imuReady && imu.getEvent(&accel, &gyro, &temp);
  Serial.print('{');
  field("probe_c", surface == DEVICE_DISCONNECTED_C ? NAN : surface, false);
  field("air_c", air.readTemperature(), true);
  field("humidity_pct", air.readHumidity(), true);
  field("ax", ok ? accel.acceleration.x : NAN, true);
  field("ay", ok ? accel.acceleration.y : NAN, true);
  field("az", ok ? accel.acceleration.z : NAN, true);
  Serial.println('}');
  delay(2500);
}
