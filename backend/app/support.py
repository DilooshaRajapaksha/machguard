from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from . import db, security, users

router = APIRouter(prefix="/support")


def init():
    with db.connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS support_requests (
            id INTEGER PRIMARY KEY, requester INTEGER NOT NULL REFERENCES users(id),
            machine_id TEXT, subject TEXT NOT NULL, description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Open', reply TEXT NOT NULL DEFAULT '',
            created TEXT NOT NULL, updated TEXT NOT NULL)""")


class Ticket(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    subject: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=4000)
    machine_id: str | None = None


class Response(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    status: Literal["Open", "In progress", "Resolved"]
    reply: str = Field(max_length=4000)


@router.get("")
def inbox(user=Depends(security.current_user)):
    with db.connect() as conn:
        return [dict(row) for row in conn.execute("""
            SELECT t.*, u.full_name FROM support_requests t JOIN users u ON u.id=t.requester
            WHERE ?='admin' OR requester=? ORDER BY updated DESC,id DESC
        """, (user["role"], user["id"]))]


@router.post("", status_code=201)
def submit(body: Ticket, user=Depends(security.current_user)):
    with db.connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        if body.machine_id and not conn.execute("""
            SELECT 1 FROM machines m LEFT JOIN engineer_accounts a ON a.engineer_id=m.engineer_id
            WHERE m.machine_id=? AND (?='admin' OR a.user_id=?)
        """, (body.machine_id,user["role"],user["id"])).fetchone():
            raise HTTPException(403, "Select one of your assigned machines.")
        stamp = users.now()
        ticket = conn.execute("""INSERT INTO support_requests
            (requester,machine_id,subject,description,created,updated) VALUES(?,?,?,?,?,?)""",
            (user["id"],body.machine_id or None,body.subject,body.description,stamp,stamp))
        return {"id": ticket.lastrowid}


@router.patch("/{ticket_id}")
def respond(ticket_id: int, body: Response, admin=Depends(security.require_admin)):
    with db.connect() as conn:
        result = conn.execute("UPDATE support_requests SET reply=?,status=?,updated=? WHERE id=?",
                              (body.reply,body.status,users.now(),ticket_id))
        if not result.rowcount:
            raise HTTPException(404, "Request not found.")
    return {"saved": True}
