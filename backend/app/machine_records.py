from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from . import db, security, maintenance_guidance

router = APIRouter(prefix="/equipment", dependencies=[Depends(security.current_user)])

SCHEMA = """
CREATE TABLE IF NOT EXISTS equipment_notes (
 machine INTEGER PRIMARY KEY, description TEXT NOT NULL, probe_location TEXT NOT NULL,
 operating_load TEXT NOT NULL, approved_range TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS service_entries (
 id INTEGER PRIMARY KEY, machine INTEGER NOT NULL, serviced TEXT NOT NULL, due TEXT,
 symptom TEXT NOT NULL, outcome TEXT NOT NULL, author TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS machine_manuals (
 id INTEGER PRIMARY KEY, machine INTEGER NOT NULL, kind TEXT NOT NULL, name TEXT NOT NULL,
 content BLOB NOT NULL, excerpt TEXT NOT NULL DEFAULT '', editor TEXT NOT NULL, edited TEXT NOT NULL, UNIQUE(machine,kind));
CREATE TABLE IF NOT EXISTS resource_edits (
 id INTEGER PRIMARY KEY, machine INTEGER NOT NULL, resource TEXT NOT NULL,
 editor TEXT NOT NULL, edited TEXT NOT NULL);
"""


def init():
    with db.connect() as conn:
        conn.executescript(SCHEMA)


def access(conn, code, user, private=False):
    machine = conn.execute("""
        SELECT m.id,m.machine_id,m.name,m.model,m.location,m.status,e.name AS engineer,
               a.user_id AS owner FROM machines m LEFT JOIN engineers e ON e.id=m.engineer_id
               LEFT JOIN engineer_accounts a ON a.engineer_id=e.id WHERE m.machine_id=?
    """, (code,)).fetchone()
    if not machine:
        raise HTTPException(404, "Machine not found.")
    allowed = user["role"] == "admin" or machine["owner"] == user["id"]
    if private and not allowed:
        raise HTTPException(403, "This action requires a machine assignment.")
    return machine, allowed


class Notes(BaseModel):
    description: str = Field(max_length=2000)
    probe_location: str = Field(max_length=200)
    operating_load: str = Field(max_length=200)
    approved_range: str = Field(max_length=300)


class Service(BaseModel):
    serviced: date
    due: date | None = None
    symptom: str = Field(min_length=2,max_length=500)
    outcome: str = Field(min_length=2,max_length=2000)


def audit(conn, machine, label, user):
    conn.execute("INSERT INTO resource_edits(machine,resource,editor,edited) VALUES(?,?,?,?)",
                 (machine,label,user["username"],datetime.now(timezone.utc).isoformat()))


@router.get("")
def directory():
    with db.connect() as conn:
        return [dict(r) for r in conn.execute("""SELECT m.machine_id,m.name,m.status,c.id AS category_id,c.name AS category_name,
            CASE WHEN n.reading_time >= strftime('%s','now') - 15 THEN
                CASE n.status WHEN 'normal' THEN 'Healthy' WHEN 'fault' THEN 'Needs attention' ELSE 'Unknown' END
                ELSE 'Unknown' END AS probe_health
            FROM machines m JOIN machine_categories c ON c.id=m.category_id
            LEFT JOIN notification_state n ON n.machine_id=m.machine_id AND n.source='measured'
            AND n.stream_id='surface-probe-1' ORDER BY c.name,m.name""")]


@router.get("/{code}")
def detail(code: str, user=Depends(security.current_user)):
    with db.connect() as conn:
        conn.execute("BEGIN")
        row, allowed = access(conn,code,user)
        machine = dict(row)
        machine.pop("owner")
        key = (row["id"],)
        notes = conn.execute("SELECT description,probe_location,operating_load,approved_range FROM equipment_notes WHERE machine=?",key).fetchone()
        pred = conn.execute("SELECT issued,due,limit_c,projected_c,predicted,actual,result FROM motor_forecasts WHERE registry_id=? ORDER BY id DESC LIMIT 1",key).fetchone()
        result = dict(machine=machine, can_edit=allowed, notes=dict(notes) if notes else {}, forecast=dict(pred) if pred else None)
        health = conn.execute("""
            SELECT status FROM notification_state WHERE machine_id=? AND source='measured'
            AND stream_id='surface-probe-1' AND reading_time >= strftime('%s','now') - 15
        """, (machine["machine_id"],)).fetchone()
        result["probe_health"] = {"normal": "Healthy", "fault": "Needs attention"}.get(
            health["status"] if health else None, "Unknown")
        if allowed:
            result["services"] = [dict(r) for r in conn.execute("SELECT * FROM service_entries WHERE machine=? ORDER BY serviced DESC,id DESC",key)]
            result["reports"] = [dict(r) for r in conn.execute("SELECT title,notes,created_at,created_by FROM maintenance_reports WHERE machine_id=? ORDER BY id DESC",key)]
            result["manuals"] = [dict(r) for r in conn.execute("SELECT kind,name,editor,edited,excerpt FROM machine_manuals WHERE machine=?",key)]
            result["forecasts"] = [dict(r) for r in conn.execute("SELECT issued,predicted,actual,result,limit_c FROM motor_forecasts WHERE registry_id=? ORDER BY id DESC LIMIT 20",key)]
            result["edits"] = [dict(r) for r in conn.execute("SELECT resource,editor,edited FROM resource_edits WHERE machine=? ORDER BY id DESC LIMIT 50",key)]
        return result


@router.put("/{code}/notes")
def save_notes(code: str, body: Notes, user=Depends(security.current_user)):
    with db.connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row,_ = access(conn,code,user,True)
        conn.execute("INSERT OR REPLACE INTO equipment_notes VALUES(?,?,?,?,?)",(row["id"],body.description,body.probe_location,body.operating_load,body.approved_range))
        audit(conn,row["id"],"Machine description and operating notes",user)
    return {"saved":True}


@router.post("/{code}/services")
def add_service(code: str, body: Service, user=Depends(security.current_user)):
    if body.due and body.due < body.serviced:
        raise HTTPException(422,"Next service must be on or after the service date.")
    with db.connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row,_ = access(conn,code,user,True)
        conn.execute("INSERT INTO service_entries(machine,serviced,due,symptom,outcome,author) VALUES(?,?,?,?,?,?)",
                     (row["id"],body.serviced.isoformat(),body.due.isoformat() if body.due else None,body.symptom,body.outcome,user["username"]))
        audit(conn,row["id"],"Service record",user)
    return {"saved":True}


ManualKind = Literal["user","parts","error-code"]


@router.put("/{code}/manuals/{kind}")
async def upload(code: str, kind: ManualKind, request: Request, name: str = Query(min_length=1,max_length=150), excerpt: str = Query(default="",max_length=1000), user=Depends(security.current_user)):
    with db.connect() as conn:
        access(conn,code,user,True)
    data = bytearray()
    async for chunk in request.stream():
        if len(data)+len(chunk)>5*1024*1024:
            raise HTTPException(413,"Maximum PDF size is 5 MB.")
        data.extend(chunk)
    if not data.startswith(b"%PDF-"):
        raise HTTPException(422,"Choose a PDF file.")
    with db.connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row,_ = access(conn,code,user,True)
        conn.execute("INSERT OR REPLACE INTO machine_manuals(machine,kind,name,content,excerpt,editor,edited) VALUES(?,?,?,?,?,?,?)",
                     (row["id"],kind,name,data,excerpt,user["username"],datetime.now(timezone.utc).isoformat()))
        audit(conn,row["id"],kind+" manual: "+name,user)
    return {"saved":True}


@router.get("/{code}/manuals/{kind}")
def download(code: str, kind: ManualKind, user=Depends(security.current_user)):
    with db.connect() as conn:
        row,_ = access(conn,code,user,True)
        manual = conn.execute("SELECT content FROM machine_manuals WHERE machine=? AND kind=?",(row["id"],kind)).fetchone()
        if not manual:
            raise HTTPException(404,"Manual not found.")
        return Response(manual["content"],media_type="application/pdf",headers={"Content-Disposition":'attachment; filename="manual.pdf"'})


class Question(BaseModel):
    question: str = Field(min_length=2,max_length=500)


@router.post("/{code}/guidance")
def guidance(code: str, body: Question, user=Depends(security.current_user)):
    record = detail(code,user)
    if not record["can_edit"]:
        raise HTTPException(403,"Machine assignment required.")
    return maintenance_guidance.answer(record, body.question)
