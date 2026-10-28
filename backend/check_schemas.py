from pydantic import ValidationError
from app.schemas import Reading

print("Test 1: a normal compressor reading")
r = Reading(machine_id="compressor-1", discharge_pressure_bar=7.5,
            discharge_temp_c=82, oil_temp_c=70, motor_current_a=45)
print("  accepted ->", r.machine_id, r.discharge_temp_c, "C")

print("Test 2: temperature sent as the text 'banana'")
try:
    Reading(machine_id="compressor-1", discharge_pressure_bar=7.5,
            discharge_temp_c="banana", oil_temp_c=70, motor_current_a=45)
    print("  accepted (this should not happen)")
except ValidationError as e:
    print("  rejected ->", e.errors()[0]["loc"][0], "is not a valid number")

print("Test 3: temperature of 500 C (impossible)")
try:
    Reading(machine_id="compressor-1", discharge_pressure_bar=7.5,
            discharge_temp_c=500, oil_temp_c=70, motor_current_a=45)
    print("  accepted (this should not happen)")
except ValidationError as e:
    print("  rejected ->", e.errors()[0]["loc"][0], "is out of range")
