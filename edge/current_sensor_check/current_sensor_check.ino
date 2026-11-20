constexpr int currentPin = 34;

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  analogSetPinAttenuation(currentPin, ADC_11db);
}

void loop() {
  unsigned long total = 0;
  for (int i = 0; i < 100; i++) {
    total += analogReadMilliVolts(currentPin);
    delay(2);
  }
  Serial.printf("GPIO34: %.3f V\n", total / 100000.0);
  delay(1000);
}
