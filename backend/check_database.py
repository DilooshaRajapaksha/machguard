import os
import tempfile

# Use a throw-away diary so we never touch the real one
os.environ["MACHGUARD_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")

from app import db
from app.simulator import Scenario, generate

db.init_db()
print("1. Diary created:", db.DB_FILE.name)

for r in generate(Scenario.SLOW_OVERHEATING, steps=120):
    db.save_reading(r)
rows = db.latest_readings(limit=1000)
print("2. Readings saved:", len(rows), "(expected 120)")

events = db.fault_events()
print("3. Fault events logged:", len(events), "(expected 1, not one per reading)")
print("   first fault:", events[0]["fault_code"])

newest = db.latest_readings(limit=1)[0]
print("4. Newest reading temp:", newest["discharge_temp_c"], "C")

db.clear_all()
print("5. After clear_all:", len(db.latest_readings()), "readings left")