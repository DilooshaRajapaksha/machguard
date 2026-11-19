from . import db
from .schemas import Reading


def init():
    with db.connect() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS demo_samples(id INTEGER PRIMARY KEY, machine_id TEXT NOT NULL, sample TEXT NOT NULL)")


def save(rows):
    with db.connect() as conn:
        conn.executemany("INSERT INTO demo_samples(machine_id,sample) VALUES(?,?)",
                         [(r.machine_id,r.model_dump_json()) for r in rows])


def latest(machine_id, limit):
    with db.connect() as conn:
        rows = conn.execute("SELECT sample FROM demo_samples WHERE machine_id=? ORDER BY id DESC LIMIT ?",(machine_id,limit))
        return list(reversed([Reading.model_validate_json(r["sample"]) for r in rows]))


def reset():
    with db.connect() as conn:
        conn.execute("DELETE FROM demo_samples")

