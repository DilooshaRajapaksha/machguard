import asyncio
import time
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException

from . import chat_service, db, security
from .chat_schemas import ChatRequest, EnergyRequest


router = APIRouter(prefix="/chat", tags=["chat"], dependencies=[Depends(security.current_user)])


def owned_conversation(conn, conversation_id, user_id):
    row = conn.execute("SELECT * FROM chat_conversations WHERE id=? AND user_id=?",
                       (str(conversation_id), user_id)).fetchone()
    if row is None:
        raise HTTPException(404, "Conversation not found.")
    return dict(row)


@router.get("/status")
def status():
    return {"configured": all(chat_service.settings().values()), "provider": "Google Gemini"}


@router.get("/machines")
def machines():
    with db.connect() as conn:
        return [row[0] for row in conn.execute("SELECT machine_id FROM machines ORDER BY name")]


@router.get("/conversations")
def conversations(user: dict = Depends(security.current_user)):
    with db.connect() as conn:
        return [dict(row) for row in conn.execute(
            "SELECT * FROM chat_conversations WHERE user_id=? ORDER BY created_at DESC LIMIT 50", (user["id"],))]


@router.get("/conversations/{conversation_id}")
def conversation(conversation_id: UUID, user: dict = Depends(security.current_user)):
    with db.connect() as conn:
        result = owned_conversation(conn, conversation_id, user["id"])
        result["messages"] = [dict(row) for row in conn.execute(
            "SELECT role,content,created_at FROM chat_messages WHERE conversation_id=? ORDER BY id", (str(conversation_id),))]
    return result


@router.post("/energy")
def energy(body: EnergyRequest):
    return {"estimated_kg_co2e": round(body.energy_kwh * body.emission_factor, 4),
            "kwh_per_unit": round(body.energy_kwh / body.production_units, 6),
            "factor_source": body.factor_source,
            "basis": "User-entered values; factor applicability and measurements must be verified."}


@router.post("/messages")
async def send_message(body: ChatRequest, user: dict = Depends(security.current_user)):
    config = chat_service.settings()
    if not all(config.values()):
        raise HTTPException(503, "Chat is not configured. Add GEMINI_API_KEY and GEMINI_MODEL to backend/.env.")
    conversation_id = str(body.conversation_id or uuid4())
    with db.connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        if body.conversation_id:
            existing = owned_conversation(conn, conversation_id, user["id"])
            if body.machine_id != existing["machine_id"]:
                raise HTTPException(409, "Start a new conversation to change machines.")
        history = [dict(row) for row in conn.execute(
            "SELECT role,content FROM chat_messages WHERE conversation_id=? ORDER BY id DESC LIMIT 12", (conversation_id,))][::-1]
        request = conn.execute("SELECT * FROM chat_requests WHERE user_id=?", (user["id"],)).fetchone()
        now = time.time()
        if request and (request["busy_until"] > now or now - request["started_at"] < 5):
            raise HTTPException(429, "Please wait a moment before sending another message.")
        conn.execute("INSERT INTO chat_requests VALUES (?,?,?) ON CONFLICT(user_id) DO UPDATE SET started_at=excluded.started_at,busy_until=excluded.busy_until",
                     (user["id"], now, now + 240))
    try:
        context = chat_service.machine_context(body.machine_id)
        history.append({"role": "user", "content": body.message})
        try:
            reply = await asyncio.wait_for(chat_service.generate_reply(history, context, config), timeout=50)
        except TimeoutError:
            raise HTTPException(503, "The AI service took too long. Please try again.") from None
        timestamp = chat_service.now_text()
        with db.connect() as conn:
            conn.execute("INSERT OR IGNORE INTO chat_conversations VALUES (?,?,?,?,?)",
                         (conversation_id, user["id"], body.machine_id, body.message[:80], timestamp))
            conn.executemany("INSERT INTO chat_messages (conversation_id,role,content,created_at) VALUES (?,?,?,?)",
                             [(conversation_id, "user", body.message, timestamp), (conversation_id, "assistant", reply, timestamp)])
        return {"conversation_id": conversation_id, "reply": reply, "context": context}
    finally:
        with db.connect() as conn:
            conn.execute("UPDATE chat_requests SET busy_until=0 WHERE user_id=? AND started_at=?", (user["id"], now))
