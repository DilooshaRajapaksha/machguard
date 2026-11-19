from datetime import datetime, timedelta

SCHEMA = """
CREATE TABLE IF NOT EXISTS motor_forecasts (
 id INTEGER PRIMARY KEY, registry_id INTEGER NOT NULL, issued TEXT NOT NULL,
 due TEXT NOT NULL, limit_c REAL NOT NULL, projected_c REAL NOT NULL,
 predicted INTEGER NOT NULL, actual INTEGER, result TEXT NOT NULL,
 last_seen TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_motor_forecasts ON motor_forecasts(registry_id,id);
"""


def update(conn, registry_id, stamp, temperature, limit):
    now = datetime.fromisoformat(stamp)
    previous = conn.execute("SELECT * FROM motor_forecasts WHERE registry_id=? ORDER BY id DESC LIMIT 1", (registry_id,)).fetchone()
    if previous and previous["result"] == "pending":
        gap = (now - datetime.fromisoformat(previous["last_seen"])).total_seconds()
        expired = stamp >= previous["due"]
        if gap > 30 or temperature is None:
            result = "insufficient coverage"
        elif not expired and temperature >= previous["limit_c"]:
            result = "crossed"
        elif expired:
            result = "below limit"
            if temperature >= previous["limit_c"]:
                result = "crossed" if stamp == previous["due"] else "insufficient coverage"
        else:
            result = "pending"
        actual = {"crossed": 1, "below limit": 0}.get(result)
        conn.execute("UPDATE motor_forecasts SET result=?, actual=?, last_seen=? WHERE id=?", (result, actual, stamp, previous["id"]))
    if previous and stamp < previous["due"]:
        return
    if temperature is None or limit is None or temperature >= limit:
        return
    rows = conn.execute("""
        SELECT received_at, json_extract(sample,'$.probe_c') AS temp FROM bench_samples
        WHERE registry_id=? AND received_at>=? ORDER BY received_at,id
    """, (registry_id, (now-timedelta(minutes=5)).isoformat())).fetchall()
    times = [(datetime.fromisoformat(r["received_at"])-now).total_seconds()/60 for r in rows]
    if len(rows)<8 or times[0]>-1 or any(r["temp"] is None for r in rows):
        return
    if any(b-a>0.5 for a,b in zip(times,times[1:])):
        return
    mean = sum(times)/len(times)
    slope = sum((t-mean)*r["temp"] for t,r in zip(times,rows))/sum((t-mean)**2 for t in times)
    projected = temperature + slope*15
    due = (now+timedelta(minutes=15)).isoformat()
    conn.execute("""
        INSERT INTO motor_forecasts(registry_id,issued,due,limit_c,projected_c,predicted,result,last_seen)
        VALUES(?,?,?,?,?,?,'pending',?)
    """, (registry_id,stamp,due,limit,projected,int(projected>=limit),stamp))

