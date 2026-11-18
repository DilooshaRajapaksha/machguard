from app.ai import analyse
from app.simulator import Scenario, generate

MIN_NEEDED = 8
STEPS = 120

print("Early-warning AI test: 120 readings per story, one reading per minute\n")

for s in Scenario:
    data = generate(s, steps=STEPS)
    first_warning = None
    first_fault = None
    for i in range(MIN_NEEDED, STEPS + 1):
        result = analyse(data[:i])
        if first_warning is None and result["status"] == "warning":
            first_warning = i
        if first_fault is None and result["status"] == "fault":
            first_fault = i
    print(s.value)
    if first_warning is None and first_fault is None:
        print("  no warning, no fault (correct for a healthy day)" if s == Scenario.HEALTHY else "  nothing happened")
    else:
        if first_warning:
            print("  early warning at minute", first_warning)
        else:
            print("  early warning: none")
        if first_fault:
            print("  fault code at minute  ", first_fault)
        if first_warning and first_fault:
            print("  warned", first_fault - first_warning, "minutes before the fault")
    print()

false_alarms = 0
runs = 0
for seed in range(50, 80):
    data = generate(Scenario.HEALTHY, steps=STEPS, seed=seed)
    for i in range(MIN_NEEDED, STEPS + 1):
        runs += 1
        if analyse(data[:i])["status"] in ("warning", "fault"):
            false_alarms += 1
print("False alarms on 30 healthy days:", false_alarms, "out of", runs, "checks")