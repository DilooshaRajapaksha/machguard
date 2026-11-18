from app.simulator import Scenario, generate
from app.codes import CARDS

STEPS = 120
print("Pretend compressor: %d readings per story\n" % STEPS)

for s in Scenario:
    data = generate(s, steps=STEPS)
    first_fault = next((i for i, r in enumerate(data) if r.fault_code), None)
    print(s.value)
    print("  temperature: %.1f -> %.1f C" % (data[0].discharge_temp_c, data[-1].discharge_temp_c))
    print("  vibration:   %.2f -> %.2f" % (data[0].vibration_rms, data[-1].vibration_rms))
    print("  current:     %.1f -> %.1f A" % (data[0].motor_current_a, data[-1].motor_current_a))
    if first_fault is None:
        print("  fault code:  none the whole time")
    else:
        code = data[first_fault].fault_code
        print("  fault code:  %s first shows at reading %d of %d (%s)"
              % (code, first_fault + 1, STEPS, CARDS[code].title))
    print()

same = generate(Scenario.SLOW_OVERHEATING, steps=10, seed=1)
again = generate(Scenario.SLOW_OVERHEATING, steps=10, seed=1)
print("Same seed gives the same story:",
      [r.discharge_temp_c for r in same] == [r.discharge_temp_c for r in again])