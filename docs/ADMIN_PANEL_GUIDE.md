# MachGuard admin dashboard — full copy-paste source

Follow INSTALL_ADMIN_PANEL.md first. Existing React files in frontend/app are unchanged. The new panel lives in frontend/admin-dashbord and runs at /panel on the FastAPI server.

## backend/app/registry_routes.py

```python
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

```

## backend/check_registry.py

```python
"""Run with: python check_registry.py (uses a temporary database)."""
import os
import tempfile
import unittest

temporary = tempfile.TemporaryDirectory()
os.environ["MACHGUARD_DB"] = os.path.join(temporary.name, "registry-test.db")
os.environ["MACHGUARD_SECRET"] = "registry-test-only-secret-01234567890123456789"

from fastapi.testclient import TestClient
from app import db, security, users
from app.main import app
from app.registry_routes import init_registry

class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        with db.connect() as conn:
            for table in ("maintenance_reports", "machines", "engineers", "machine_categories", "users"):
                conn.execute(f"DELETE FROM {table}")
        for username, role, change in (("boss", "admin", False), ("viewer", "viewer", False), ("newadmin", "admin", True)):
            users.create(username, username, security.hash_password("Testing-Pass-123"), role, change)
        token = self.client.post("/auth/login", json={"username":"boss", "password":"Testing-Pass-123"}).json()["access_token"]
        self.headers = {"Authorization": "Bearer " + token}
        self.base = "/admin/registry"

    def post(self, route, body):
        return self.client.post(self.base + route, json=body, headers=self.headers)

    def machine(self):
        category = self.post("/categories", {"name":"Compressor"}).json()["id"]
        engineer = self.post("/engineers", {"name":"Test Engineer", "email":"test@example.com", "specialty":"Mechanical"}).json()["id"]
        return {"machine_id":"compressor-1", "name":"Compressor 01", "category_id":category,
                "model":"Test model", "serial_number":"SN-001", "location":"Workshop",
                "status":"Working", "engineer_id":engineer}

    def test_all_routes_require_admin(self):
        routes = [("GET","",None), ("POST","/categories",{"name":"Test"}),
                  ("POST","/engineers",{}), ("POST","/machines",{}),
                  ("PUT","/machines/1",{}), ("POST","/reports",{})]
        for username, expected in ((None,401), ("viewer",403), ("newadmin",403)):
            headers = {}
            if username:
                token = self.client.post("/auth/login",json={"username":username,"password":"Testing-Pass-123"}).json()["access_token"]
                headers = {"Authorization":"Bearer "+token}
            for method, route, body in routes:
                with self.subTest(username=username, route=route):
                    self.assertEqual(self.client.request(method,self.base+route,json=body,headers=headers).status_code,expected)

    def test_full_flow_and_persistence(self):
        body = self.machine()
        response = self.post("/machines",body)
        self.assertEqual(response.status_code,201)
        machine_id = response.json()["id"]
        self.assertEqual(self.post("/reports",{"machine_id":machine_id,"title":"Inspection completed","notes":"Checked belt and recorded findings."}).status_code,201)
        body["status"] = "Maintenance"
        body["engineer_id"] = None
        self.assertEqual(self.client.put(self.base+f"/machines/{machine_id}",json=body,headers=self.headers).status_code,200)
        init_registry()  # Initialization must not erase records.
        result = self.client.get(self.base,headers=self.headers).json()
        self.assertEqual(result["machines"][0]["status"],"Maintenance")
        self.assertIsNone(result["machines"][0]["engineer_name"])
        self.assertEqual(result["reports"][0]["created_by"],"boss")
        self.assertEqual(len(result["categories"]),1)

    def test_duplicate_and_bad_references(self):
        body = self.machine()
        self.assertEqual(self.post("/machines",body).status_code,201)
        self.assertEqual(self.post("/machines",body).status_code,409)
        self.assertEqual(self.post("/categories",{"name":"compressor"}).status_code,409)
        self.assertEqual(self.post("/engineers",{"name":"Other Person","email":"TEST@example.com","specialty":"Electrical"}).status_code,409)
        body["category_id"] = 999999
        self.assertEqual(self.post("/machines",body).status_code,404)
        self.assertEqual(self.post("/reports",{"machine_id":999999,"title":"Inspection","notes":"Missing machine"}).status_code,404)

    def test_validation(self):
        self.assertEqual(self.post("/categories",{"name":"  "}).status_code,422)
        self.assertEqual(self.post("/engineers",{"name":"Someone","email":"invalid","specialty":"Mechanical"}).status_code,422)
        body = self.machine()
        body["status"] = "Unknown"
        self.assertEqual(self.post("/machines",body).status_code,422)

    def test_panel_assets(self):
        for path in ("/panel","/panel-static/styles.css","/panel-static/app.js"):
            self.assertEqual(self.client.get(path).status_code,200)

if __name__ == "__main__":
    try:
        unittest.main()
    finally:
        temporary.cleanup()

```

## frontend/admin-dashbord/index.html

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MachGuard | Dockyard administration</title>
  <link rel="stylesheet" href="/panel-static/styles.css">
  <script src="/panel-static/app.js" defer></script>
</head>
<body>
<section id="login-view" class="login-wrap">
  <form id="login-form" class="login-card">
    <div class="brand-mark">M</div><p class="eyebrow">NOVAFODGE / MACHGUARD</p>
    <h1>Welcome back.</h1><p class="muted">Sign in to manage your dockyard equipment.</p>
    <label>Username<input name="username" autocomplete="username" required></label>
    <label>Password<input name="password" type="password" autocomplete="current-password" required></label>
    <button class="primary" type="submit">Sign in →</button>
    <p id="login-error" class="error" role="alert"></p>
  </form>
</section>
<section id="password-view" class="login-wrap" hidden>
  <form id="password-form" class="login-card">
    <p class="eyebrow">ACCOUNT SECURITY</p><h1>Choose a new password.</h1>
    <p class="muted">Use at least 10 characters, including a letter and a number. Do not include your username.</p>
    <label>Current password<input name="current_password" type="password" autocomplete="current-password" required></label>
    <label>New password<input name="new_password" type="password" autocomplete="new-password" minlength="10" required></label>
    <button class="primary" type="submit">Save password</button>
    <p id="password-error" class="error" role="alert"></p>
    <button type="button" id="password-back">Back to sign in</button>
  </form>
</section>
<div id="workspace" class="workspace" hidden>
  <aside>
    <div class="brand"><span class="brand-mark">M</span><div>MachGuard<small>BY NOVAFODGE</small></div></div>
    <p class="nav-label">WORKSPACE</p>
    <nav aria-label="Main navigation">
      <button data-page="Home">⌂ <span>Home</span></button>
      <button data-page="Engineers">♙ <span>Engineers</span></button>
      <button data-page="Machines">▦ <span>Machines</span></button>
      <button data-page="Reports">▤ <span>Reports</span></button>
    </nav>
    <div class="sidebar-note"><span class="dot"></span> Dockyard administration<small>Equipment registry & maintenance</small></div>
    <button id="logout">Sign out →</button>
  </aside>
  <main>
    <header><span>Colombo Dockyard / <strong id="breadcrumb">Home</strong></span><span class="admin-chip">Administrator</span></header>
    <div class="heading"><div><p class="eyebrow">EQUIPMENT OPERATIONS</p><h1 id="page-title">Dockyard overview</h1><p id="subtitle" class="muted"></p></div><button id="refresh">↻ Refresh</button></div>
    <p id="notice" role="status"></p>
    <div id="content"></div>
    <footer>MachGuard · Read-only equipment monitoring. This panel never controls a machine.</footer>
  </main>
</div>
<dialog id="modal" aria-labelledby="modal-title">
  <form id="record-form">
    <div class="modal-heading"><h2 id="modal-title"></h2><button type="button" id="close-modal" aria-label="Close dialog">✕</button></div>
    <div id="fields"></div><p id="form-error" class="error" role="alert"></p>
    <div class="modal-actions"><button type="button" id="cancel-modal">Cancel</button><button type="submit" class="primary" id="save">Save record</button></div>
  </form>
</dialog>
</body>
</html>

```

## frontend/admin-dashbord/styles.css

```css
:root{font-family:Inter,Segoe UI,Arial,sans-serif;color:#162c3a;background:#f3f6f8;font-synthesis:none}*{box-sizing:border-box}body{margin:0}[hidden]{display:none!important}button,input,select,textarea{font:inherit}button{cursor:pointer;border:1px solid #d4dfe5;border-radius:8px;background:white;color:#223e50;padding:11px 17px;font-weight:600}button:hover{background:#edf5f6}button:disabled{opacity:.55;cursor:wait}button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:3px solid #5fb8e5;outline-offset:3px}.primary{background:#087f83;border-color:#087f83;color:white}.primary:hover{background:#06676b}.workspace{display:grid;grid-template-columns:235px 1fr;min-height:100vh}aside{background:#102c3e;color:#e6f0f4;padding:32px 22px;display:flex;flex-direction:column}.brand{display:flex;align-items:center;gap:12px;font-size:22px;font-weight:750}.brand-mark{display:inline-grid;place-items:center;background:#25b8a8;color:#082a36;width:40px;height:40px;border-radius:10px;font-size:24px;font-weight:800}.brand small,aside small{display:block;font-size:10px;letter-spacing:2px;margin-top:7px;color:#9dbac9}.nav-label{font-size:10px;letter-spacing:2px;color:#88a6b6;margin:52px 12px 15px}nav{display:grid;gap:9px}nav button{border:0;background:transparent;color:#b8ceda;text-align:left;display:flex;gap:14px;font-size:17px;padding:14px}nav button.active{background:#1d495b;color:#fff}nav button:hover{background:#244b5c}.sidebar-note{margin-top:auto;padding:60px 0 25px;font-size:12px;line-height:1.7}.sidebar-note small{letter-spacing:0}.dot{display:inline-block;border-radius:50%;background:#47c6aa;width:7px;height:7px;margin-right:5px}#logout{background:transparent;color:#d2e2e9;border-color:#395363}main{min-width:0;padding:0 38px}header{min-height:85px;border-bottom:1px solid #dce5ea;display:flex;align-items:center;justify-content:space-between;font-size:12px;color:#71838e}.admin-chip{background:white;border:1px solid #dce5ea;border-radius:30px;padding:8px 14px;color:#294453}.heading{display:flex;justify-content:space-between;align-items:center;margin:35px 0 20px;gap:15px}.eyebrow{font-size:10px;letter-spacing:2px;font-weight:750;color:#078389}h1{font-size:32px;letter-spacing:-1px;margin:9px 0 12px}h2{font-size:19px;margin:0}h3{margin:0 0 8px}.muted{color:#6c808c;font-size:14px;line-height:1.6}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin:25px 0}.stat,.panel{background:white;border:1px solid #dde6eb;border-radius:12px;padding:24px}.stat p{color:#6c808c;font-size:13px;margin:0}.stat strong{font-size:37px;font-weight:650;display:block;margin:15px 0 6px}.stat small{color:#8395a0;font-size:11px}.stat:first-child{border-top:3px solid #08938e}.panel{margin-top:22px}.section-head{display:flex;justify-content:space-between;align-items:center;gap:15px;margin-bottom:22px}.actions{display:flex;gap:10px;flex-wrap:wrap}.shortcuts{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:20px}.shortcuts button{text-align:left;padding:24px;background:#f7fafb;border-color:#e3eaee}.shortcuts span{display:block;font-size:12px;font-weight:400;color:#71838e;margin-top:8px}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;text-align:left;font-size:13px}th{font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#738893;padding:15px 12px;background:#f6f9fa}td{padding:18px 12px;border-bottom:1px solid #edf1f4}td small{display:block;color:#7d909b;margin-top:5px}.badge{display:inline-block;padding:6px 9px;border-radius:5px;background:#e7f6f0;color:#147053;font-size:11px;white-space:nowrap}.badge.Maintenance{background:#fff2da;color:#986218}.badge.Stopped{background:#eef0f3;color:#596673}.empty{padding:28px;text-align:center;color:#6c808c;line-height:1.8}.category-list{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px}.category-list span{border:1px solid #dce6ea;padding:9px 12px;border-radius:7px;font-size:13px}.report{padding:20px 0;border-bottom:1px solid #e7edf0}.report p{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.65;font-size:14px}.report small{color:#738893}footer{font-size:11px;color:#8799a4;margin:35px 0}.login-wrap{min-height:100vh;display:grid;place-items:center;padding:20px;background:#102c3e}.login-card{width:min(440px,100%);background:white;padding:38px;border-radius:16px}.login-card button.primary{width:100%;margin-top:12px}label{display:block;font-size:13px;font-weight:600;margin:17px 0}input,select,textarea{display:block;width:100%;padding:11px;border:1px solid #cbd9e1;border-radius:7px;margin-top:7px;background:white;color:#183547}textarea{min-height:110px;resize:vertical}.error{color:#a33030;font-size:13px;line-height:1.5}#notice{font-size:13px;color:#176753;min-height:18px}#notice.error{color:#a33030}dialog{border:0;border-radius:14px;max-width:540px;width:calc(100% - 32px);max-height:90vh;padding:28px;box-shadow:0 20px 80px #102c3e44}dialog::backdrop{background:#0e253f88}.modal-heading,.modal-actions{display:flex;justify-content:space-between;align-items:center;gap:15px}.modal-actions{justify-content:flex-end;border-top:1px solid #e4ebef;padding-top:20px;margin-top:22px}.modal-heading button{border:0}.row-actions{white-space:nowrap}@media(max-width:950px){.workspace{grid-template-columns:190px 1fr}main{padding:0 20px}.stats,.shortcuts{gap:10px}.stat,.panel{padding:18px}}@media(max-width:700px){.workspace{display:block}aside{padding:18px}.brand{font-size:19px}.nav-label,.sidebar-note{display:none}nav{display:flex;margin-top:18px;flex-wrap:wrap;gap:4px}nav button{padding:10px;font-size:13px}#logout{position:absolute;right:18px;top:18px;padding:9px}header{min-height:60px}.heading{margin-top:25px}h1{font-size:27px}.stats{grid-template-columns:1fr}.stat{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px}.stat strong{margin:0;font-size:28px}.stat small{width:100%}.shortcuts{grid-template-columns:1fr}.section-head{align-items:flex-start;flex-direction:column}.admin-chip{font-size:10px}main{padding:0 16px}}

```

## frontend/admin-dashbord/app.js

```javascript
/* Same-origin API; the token stays in memory and is cleared on sign-out/reload. */
const $ = (id) => document.getElementById(id);
let token = "", page = "Home", data = {machines: [], categories: [], engineers: [], reports: []};
let formKind = "", editing = null, saving = false, loaded = false;
const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const empty = text => '<div class="empty">' + escapeHTML(text) + '</div>';

async function api(path, method = "GET", body) {
  let response;
  try {
    response = await fetch(path, {
      method, headers: {"Content-Type": "application/json", ...(token ? {Authorization: "Bearer " + token} : {})},
      ...(body === undefined ? {} : {body: JSON.stringify(body)})
    });
  } catch { throw new Error("Cannot reach the backend. Check that Uvicorn is running."); }
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && path !== "/auth/login") signOut();
    const detail = result.detail;
    throw new Error(Array.isArray(detail) ? detail.map(x => x.loc.slice(1).join(" ") + ": " + x.msg).join("; ") : detail || "Request failed.");
  }
  return result;
}
function notice(text, error = false) {
  $("notice").textContent = text;
  $("notice").className = error ? "error" : "";
}
function showView(id) {
  ["login-view","password-view","workspace"].forEach(name => $(name).hidden = name !== id);
}
function signOut() {
  token = ""; loaded = false;
  data = {machines: [], categories: [], engineers: [], reports: []};
  $("modal").close(); $("record-form").reset(); $("content").replaceChildren();
  $("login-form").reset(); $("password-form").reset();
  $("login-error").textContent = ""; $("password-error").textContent = "";
  showView("login-view");
}
async function enterWorkspace() {
  const me = await api("/auth/me");
  if (me.must_change_password) { showView("password-view"); return; }
  if (me.role !== "admin") { signOut(); throw new Error("This panel is for administrators. Please use an admin account."); }
  page = "Home"; showView("workspace"); render(); await refresh();
}
$("login-form").addEventListener("submit", async event => {
  event.preventDefault();
  const button = event.submitter;
  button.disabled = true; $("login-error").textContent = "";
  try {
    const result = await api("/auth/login", "POST", Object.fromEntries(new FormData(event.target)));
    token = result.access_token; event.target.reset(); await enterWorkspace();
  } catch (error) { $("login-error").textContent = error.message; }
  finally { button.disabled = false; }
});
$("password-form").addEventListener("submit", async event => {
  event.preventDefault(); event.submitter.disabled = true; $("password-error").textContent = "";
  try {
    const result = await api("/auth/change-password", "POST", Object.fromEntries(new FormData(event.target)));
    token = result.access_token; event.target.reset(); await enterWorkspace();
  } catch (error) { $("password-error").textContent = error.message; }
  finally { event.submitter.disabled = false; }
});
$("logout").onclick = signOut;
$("password-back").onclick = signOut;
async function refresh() {
  $("refresh").disabled = true; notice("Loading records…");
  try { data = await api("/admin/registry"); loaded = true; render(); notice("Records are up to date."); }
  catch (error) { notice(error.message, true); }
  finally { $("refresh").disabled = false; }
}
$("refresh").onclick = refresh;
document.querySelectorAll("[data-page]").forEach(button => {
  button.onclick = () => {page = button.dataset.page; render();};
});
function stat(label, number, note) {
  return '<div class="stat"><p>'+label+'</p><strong>'+number+'</strong><small>'+note+'</small></div>';
}
function table(headers, rows) {
  return '<div class="table-wrap"><table><thead><tr>'+headers.map(h=>'<th>'+h+'</th>').join("")+'</tr></thead><tbody>'+rows.join("")+'</tbody></table></div>';
}
function machineTable(machines) {
  if (!machines.length) return empty("No machines yet. Add a category, then add your first machine.");
  return table(["Machine","Category / location","Status","Assigned engineer","Action"], machines.map(m =>
    '<tr><td><strong>'+escapeHTML(m.name)+'</strong><small>'+escapeHTML(m.machine_id)+' · '+escapeHTML(m.model)+'</small></td><td>'+escapeHTML(m.category_name)+'<small>'+escapeHTML(m.location)+'</small></td><td><span class="badge '+escapeHTML(m.status)+'">'+escapeHTML(m.status)+'</span></td><td>'+escapeHTML(m.engineer_name || "Unassigned")+'</td><td class="row-actions"><button data-edit="'+m.id+'">Edit</button></td></tr>'
  ));
}
function render() {
  $("breadcrumb").textContent = page;
  $("page-title").textContent = {Home:"Dockyard overview",Machines:"Machine registry",Engineers:"Your engineering team",Reports:"Maintenance reports"}[page];
  $("subtitle").textContent = {Home:"A clear view of your equipment, people and maintenance records.",Machines:"Organise equipment by category and assign the right engineer.",Engineers:"Keep staff details together and see their machine assignments.",Reports:"Keep a record of inspections, findings and maintenance work."}[page];
  document.querySelectorAll("[data-page]").forEach(b => {
    b.classList.toggle("active", b.dataset.page === page);
    if(b.dataset.page === page) b.setAttribute("aria-current","page"); else b.removeAttribute("aria-current");
  });
  if (!loaded) { $("content").innerHTML = empty("Records have not loaded yet. Use Refresh to try again."); return; }
  const add = (kind,label) => '<button class="primary" data-add="'+kind+'">+ '+label+'</button>';
  let html = "";
  if (page === "Home") {
    const assigned = new Set(data.machines.filter(m=>m.engineer_id).map(m=>m.engineer_id)).size;
    html = '<section class="stats">'+stat("Machines working",data.machines.filter(m=>m.status==="Working").length,"Admin-entered status · not live telemetry")+stat("Engineers assigned",assigned,"Unique engineers assigned to machines")+stat("Maintenance reports",data.reports.length,"Saved inspection and maintenance notes")+'</section><section class="panel"><h2>Quick actions</h2><p class="muted">Start with the people and equipment at your dockyard.</p><div class="shortcuts"><button data-add="machine">+ Add machine<span>Register equipment and assign an engineer</span></button><button data-add="engineer">+ Add engineer<span>Add a staff record to your team</span></button><button data-add="report">+ Create report<span>Record an inspection or maintenance task</span></button></div></section><section class="panel"><div class="section-head"><h2>Recently registered machines</h2><button data-go="Machines">View all →</button></div>'+machineTable(data.machines.slice(0,5))+'</section>';
  } else if (page === "Machines") {
    html = '<section class="stats">'+stat("Registered machines",data.machines.length,"All equipment in the registry")+stat("Machine categories",data.categories.length,"Your equipment groups")+stat("Under maintenance",data.machines.filter(m=>m.status==="Maintenance").length,"Admin-entered status")+'</section><section class="panel"><div class="section-head"><h2>Equipment</h2><div class="actions">'+add("category","Add category")+add("machine","Add machine")+'</div></div>'+machineTable(data.machines)+'</section><section class="panel"><h2>Machine categories</h2>'+(data.categories.length?'<div class="category-list">'+data.categories.map(c=>'<span>'+escapeHTML(c.name)+' · '+data.machines.filter(m=>m.category_id===c.id).length+'</span>').join("")+'</div>':empty("No categories yet. Try Compressor or Generator."))+'</section>';
  } else if(page === "Engineers") {
    html = '<section class="panel"><div class="section-head"><div><h2>Engineers · '+data.engineers.length+'</h2><p class="muted">Staff records only. Adding a person here does not create a login account.</p></div>'+add("engineer","Add engineer")+'</div>'+
      (data.engineers.length?table(["Engineer","Email","Specialty","Assigned machines"],data.engineers.map(e=>'<tr><td>'+escapeHTML(e.name)+'</td><td>'+escapeHTML(e.email)+'</td><td>'+escapeHTML(e.specialty)+'</td><td>'+escapeHTML(data.machines.filter(m=>m.engineer_id===e.id).map(m=>m.name).join(", ")||"Unassigned")+'</td></tr>')):empty("No engineers yet. Add your first team member."))+'</section>';
  } else {
    html = '<section class="panel"><div class="section-head"><h2>Reports · '+data.reports.length+'</h2>'+add("report","Create report")+'</div>'+
      (data.reports.length?data.reports.map(r=>'<article class="report"><h3>'+escapeHTML(r.title)+'</h3><small>'+escapeHTML(r.machine_name)+' · '+escapeHTML(new Date(r.created_at).toLocaleString())+' · '+escapeHTML(r.created_by)+'</small><p>'+escapeHTML(r.notes)+'</p></article>').join(""):empty("No reports yet. Register a machine, then record its first inspection."))+'</section>';
  }
  $("content").innerHTML = html;
}
$("content").addEventListener("click", event => {
  const button = event.target.closest("button");
  if (!button) return;
  if (button.dataset.go) { page = button.dataset.go; render(); }
  if (button.dataset.add) openForm(button.dataset.add);
  if (button.dataset.edit) openForm("machine", data.machines.find(m=>m.id===Number(button.dataset.edit)));
});
function input(name, label, value = "", type = "text", max = 100, min = 2) {
  return '<label>'+label+'<input name="'+name+'" type="'+type+'" value="'+escapeHTML(value)+'" required maxlength="'+max+'" minlength="'+min+'"></label>';
}
function select(name,label,items,value="",optional=false) {
  return '<label>'+label+'<select name="'+name+'" '+(optional?"":"required")+'><option value="">'+(optional?"Unassigned":"Choose…")+'</option>'+
    items.map(item=>'<option value="'+escapeHTML(item.id)+'" '+(String(item.id)===String(value)?"selected":"")+'>'+escapeHTML(item.name)+'</option>').join("")+'</select></label>';
}
function openForm(kind, record = null) {
  if (kind === "machine" && !data.categories.length) {
    notice("First add a machine category. Then you can register the machine."); kind = "category";
  }
  if (kind === "report" && !data.machines.length) { notice("Please add a machine before creating a report.", true); return; }
  formKind = kind; editing = record; $("form-error").textContent = "";
  $("modal-title").textContent = {category:"Add machine category",engineer:"Add engineer",machine:record?"Edit machine":"Add machine",report:"Create maintenance report"}[kind];
  const r = record || {};
  let fields = "";
  if(kind === "category") fields = input("name","Category name","","text",80);
  if(kind === "engineer") fields = '<p class="muted">This creates a staff record, not a sign-in account.</p>'+input("name","Full name","","text",80)+input("email","Email address","","email",150)+input("specialty","Specialty (e.g. Mechanical maintenance)");
  if(kind === "machine") fields = input("machine_id","Machine ID (e.g. compressor-1)",r.machine_id,"text",64)+input("name","Machine name",r.name)+select("category_id","Category",data.categories,r.category_id)+input("model","Model",r.model,"text",100,1)+input("serial_number","Serial number",r.serial_number,"text",100,1)+input("location","Location",r.location,"text",150)+select("status","Recorded operating status",["Stopped","Working","Maintenance"].map(s=>({id:s,name:s})),r.status||"Stopped")+select("engineer_id","Assigned engineer",data.engineers,r.engineer_id,true);
  if(kind === "report") fields = select("machine_id","Machine",data.machines)+input("title","Report title","","text",150,3)+'<label>Inspection / maintenance notes<textarea name="notes" required minlength="3" maxlength="5000"></textarea></label>';
  $("fields").innerHTML = fields; $("modal").showModal();
}
$("close-modal").onclick = $("cancel-modal").onclick = () => {if(!saving) $("modal").close();};
$("modal").addEventListener("cancel", event => {if(saving) event.preventDefault();});
$("record-form").addEventListener("submit", async event => {
  event.preventDefault(); if (saving) return;
  saving = true; $("save").disabled = true; $("form-error").textContent = "";
  const body = Object.fromEntries(new FormData(event.target));
  for (const key of ["category_id","engineer_id"]) if(key in body) body[key] = body[key] ? Number(body[key]) : null;
  if(formKind === "report") body.machine_id = Number(body.machine_id);
  const route = {category:"categories",engineer:"engineers",machine:"machines",report:"reports"}[formKind];
  try {
    await api("/admin/registry/"+route+(editing?"/"+editing.id:""),editing?"PUT":"POST",body);
    $("modal").close(); event.target.reset(); await refresh();
  } catch(error) { $("form-error").textContent = error.message; }
  finally {saving = false; $("save").disabled = false;}
});

```

## backend/app/main.py

```python
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from . import registry_routes
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import admin_routes, ai, auth_routes, codes, db, simulator
from .schemas import FaultCard, Reading

app = FastAPI(
    title="MachGuard API",
    description="Fault guidance and early warning for Kaeser Sigma Control 2 compressors",
    version="0.5.0",
)

db.init_db()
registry_routes.init_registry()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulator.router)
app.include_router(auth_routes.router)
app.include_router(admin_routes.router)

@app.get("/")
def home():
    return {"app": "MachGuard", "message": "Backend is alive"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/codes", response_model=List[FaultCard])
def all_codes():
    """Every recipe card we have."""
    return codes.list_cards()


@app.get("/codes/{code}", response_model=FaultCard)
def one_code(code: str):
    """One recipe card, looked up by its code."""
    card = codes.get_card(code)
    if card is None:
        raise HTTPException(status_code=404, detail=f"No card for code '{code}'")
    return card


@app.post("/readings")
def add_reading(reading: Reading):
    """The machine (or the simulator) hands us one reading. We write it in the diary."""
    new_id = db.save_reading(reading)
    return {"saved": True, "id": new_id}


@app.get("/readings")
def get_readings(
    machine_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
):
    """Read the diary back, newest first."""
    return db.latest_readings(machine_id, limit)


@app.get("/faults")
def get_faults(
    machine_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
):
    """Every time a new fault code showed up."""
    return db.fault_events(machine_id, limit)


@app.post("/simulator/load")
def load_story(
    scenario: simulator.Scenario = simulator.Scenario.HEALTHY,
    steps: int = Query(120, ge=1, le=2000),
    seed: int = 42,
    fraction: float = Query(1.0, gt=0, le=1),
):
    """Act out a story AND write its readings into the diary. Use fraction to stop partway."""
    readings = simulator.generate(scenario, steps=steps, seed=seed)
    keep = readings[: max(1, int(steps * fraction))]
    for r in keep:
        db.save_reading(r)
    return {"saved": len(keep), "scenario": scenario.value}


@app.get("/analysis")
def analysis(machine_id: str = "compressor-1", window: int = Query(30, ge=8, le=500)):
    """Ask the AI how the machine looks right now."""
    rows = list(reversed(db.latest_readings(machine_id, window)))
    readings = [Reading(**row) for row in rows]
    result = ai.analyse(readings)
    result["machine_id"] = machine_id
    result["readings_used"] = len(readings)
    return result


@app.post("/simulator/reset")
def reset_diary():
    """Empty the diary so a demo can start from a clean page."""
    db.clear_all()
    return {"cleared": True}

app.include_router(registry_routes.router)

ADMIN_FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend" / "admin-dashbord"
app.mount("/panel-static", StaticFiles(directory=str(ADMIN_FRONTEND_DIR)), name="panel-static")


@app.get("/panel", include_in_schema=False)
def admin_panel():
    return FileResponse(ADMIN_FRONTEND_DIR / "index.html")

```

