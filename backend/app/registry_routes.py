"""Admin registry: machines, categories, engineer records and maintenance reports."""
import sqlite3
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from . import db, security, users

router = APIRouter(prefix="/admin/registry", tags=["machine registry"],
                   dependencies=[Depends(security.require_admin)])

TABLES = """
CREATE TABLE IF NOT EXISTS machine_categories (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL UNIQUE COLLATE NOCASE
);
CREATE TABLE IF NOT EXISTS engineers (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL,
 email TEXT NOT NULL UNIQUE COLLATE NOCASE,
 specialty TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS machines (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 machine_id TEXT NOT NULL UNIQUE COLLATE NOCASE,
 name TEXT NOT NULL,
 category_id INTEGER NOT NULL REFERENCES machine_categories(id),
 model TEXT NOT NULL,
 serial_number TEXT NOT NULL UNIQUE COLLATE NOCASE,
 location TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('Working','Maintenance','Stopped')),
 engineer_id INTEGER REFERENCES engineers(id)
);
CREATE TABLE IF NOT EXISTS maintenance_reports (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 machine_id INTEGER NOT NULL REFERENCES machines(id),
 title TEXT NOT NULL,
 notes TEXT NOT NULL,
 created_at TEXT NOT NULL,
 created_by TEXT NOT NULL
);
"""


def init_registry():
    with db.connect() as conn:
        conn.executescript(TABLES)


class Form(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class CategoryIn(Form):
    name: str = Field(min_length=2, max_length=80)


class EngineerIn(Form):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(max_length=150, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    specialty: str = Field(min_length=2, max_length=100)


class MachineIn(Form):
    machine_id: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=100)
    category_id: int = Field(gt=0)
    model: str = Field(min_length=1, max_length=100)
    serial_number: str = Field(min_length=1, max_length=100)
    location: str = Field(min_length=2, max_length=150)
    status: Literal["Working", "Maintenance", "Stopped"] = "Stopped"
    engineer_id: Optional[int] = Field(default=None, gt=0)


class ReportIn(Form):
    machine_id: int = Field(gt=0)
    title: str = Field(min_length=3, max_length=150)
    notes: str = Field(min_length=3, max_length=5000)


def require_reference(conn, table, record_id, label):
    # Table names are fixed internal constants, never supplied by the caller.
    if not conn.execute(f"SELECT id FROM {table} WHERE id = ?", (record_id,)).fetchone():
        raise HTTPException(404, f"{label} does not exist.")


def insert(conn, table, values):
    columns = ", ".join(values)
    placeholders = ", ".join("?" for _ in values)
    return conn.execute(
        f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", tuple(values.values())
    ).lastrowid


@router.get("")
def registry():
    with db.connect() as conn:
        return {
            "categories": [dict(r) for r in conn.execute("SELECT * FROM machine_categories ORDER BY name")],
            "engineers": [dict(r) for r in conn.execute("SELECT * FROM engineers ORDER BY name")],
            "machines": [dict(r) for r in conn.execute("""
                SELECT m.*, c.name AS category_name, e.name AS engineer_name
                FROM machines m JOIN machine_categories c ON c.id=m.category_id
                LEFT JOIN engineers e ON e.id=m.engineer_id ORDER BY m.id DESC
            """)],
            "reports": [dict(r) for r in conn.execute("""
                SELECT r.*, m.name AS machine_name FROM maintenance_reports r
                JOIN machines m ON m.id=r.machine_id ORDER BY r.id DESC
            """)],
        }


@router.post("/categories", status_code=201)
def add_category(body: CategoryIn):
    try:
        with db.connect() as conn:
            new_id = insert(conn, "machine_categories", body.model_dump())
    except sqlite3.IntegrityError:
        raise HTTPException(409, "That machine category already exists.")
    return {"id": new_id, **body.model_dump()}


@router.post("/engineers", status_code=201)
def add_engineer(body: EngineerIn):
    try:
        with db.connect() as conn:
            new_id = insert(conn, "engineers", body.model_dump())
    except sqlite3.IntegrityError:
        raise HTTPException(409, "An engineer with that email already exists.")
    return {"id": new_id, **body.model_dump()}


def check_machine(conn, body):
    require_reference(conn, "machine_categories", body.category_id, "Category")
    if body.engineer_id is not None:
        require_reference(conn, "engineers", body.engineer_id, "Engineer")


@router.post("/machines", status_code=201)
def add_machine(body: MachineIn):
    try:
        with db.connect() as conn:
            check_machine(conn, body)
            new_id = insert(conn, "machines", body.model_dump())
    except sqlite3.IntegrityError:
        raise HTTPException(409, "The machine ID or serial number already exists.")
    return {"id": new_id, **body.model_dump()}


@router.put("/machines/{machine_id}")
def edit_machine(machine_id: int, body: MachineIn):
    try:
        with db.connect() as conn:
            require_reference(conn, "machines", machine_id, "Machine")
            check_machine(conn, body)
            values = body.model_dump()
            conn.execute(
                "UPDATE machines SET " + ", ".join(f"{key}=?" for key in values) + " WHERE id=?",
                (*values.values(), machine_id),
            )
    except sqlite3.IntegrityError:
        raise HTTPException(409, "The machine ID or serial number already exists.")
    return {"id": machine_id, **body.model_dump()}


@router.post("/reports", status_code=201)
def add_report(body: ReportIn, admin: dict = Depends(security.require_admin)):
    values = {**body.model_dump(), "created_at": users.now(), "created_by": admin["username"]}
    with db.connect() as conn:
        require_reference(conn, "machines", body.machine_id, "Machine")
        new_id = insert(conn, "maintenance_reports", values)
    return {"id": new_id, **values}
