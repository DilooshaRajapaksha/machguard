import os
import tempfile

folder = tempfile.mkdtemp()
os.environ["MACHGUARD_DB"] = os.path.join(folder, "auth_test.db")
os.environ["MACHGUARD_SECRET"] = "test-secret-key-that-is-long-enough-0123456789"

from fastapi.testclient import TestClient

from app import security, users
from app.main import app

client = TestClient(app)
passed = 0
failed = 0


def check(name, condition):
    global passed, failed
    if condition:
        passed += 1
        print("PASS ", name)
    else:
        failed += 1
        print("FAIL ", name)


def login(username, password):
    return client.post("/auth/login", json={"username": username, "password": password})


def headers(token):
    return {"Authorization": "Bearer " + token}


users.create("boss", "The Boss", security.hash_password("Strong-Pass-123"), "admin", must_change=False)

check("admin endpoints need a login", client.get("/admin/users").status_code == 401)
check("a fake token is refused", client.get("/admin/users", headers=headers("abc.def.ghi")).status_code == 401)
check("wrong password is refused", login("boss", "wrong-password-1").status_code == 401)
check("unknown user gets the same answer", login("nobody", "whatever-123").json()["detail"] == login("boss", "wrong-password-1").json()["detail"])

good = login("boss", "Strong-Pass-123")
check("admin can log in", good.status_code == 200)
admin_token = good.json()["access_token"]
check("admin can see the user list", client.get("/admin/users", headers=headers(admin_token)).status_code == 200)
check("password hashes are never shown", "password_hash" not in client.get("/admin/users", headers=headers(admin_token)).text)

weak = client.post("/admin/users", headers=headers(admin_token), json={"username": "sam", "full_name": "Sam Silva", "password": "short1"})
check("weak password is refused", weak.status_code == 400)
no_digit = client.post("/admin/users", headers=headers(admin_token), json={"username": "sam", "full_name": "Sam Silva", "password": "onlyletterslong"})
check("password without a number is refused", no_digit.status_code == 400)

made = client.post("/admin/users", headers=headers(admin_token), json={"username": "sam", "full_name": "Sam Silva", "password": "Temp-Pass-2026", "role": "viewer"})
check("admin can add a person", made.status_code == 201)
check("same username again is refused", client.post("/admin/users", headers=headers(admin_token), json={"username": "SAM", "full_name": "Sam Two", "password": "Temp-Pass-2026"}).status_code == 409)

sam = login("sam", "Temp-Pass-2026")
check("the new person can log in", sam.status_code == 200)
check("and is told to change the password", sam.json()["must_change_password"] is True)
sam_token = sam.json()["access_token"]
check("they can see their own profile", client.get("/auth/me", headers=headers(sam_token)).status_code == 200)
blocked = client.get("/admin/users", headers=headers(sam_token))
check("but nothing else until they change it", blocked.status_code == 403 and blocked.json()["detail"] == "password_change_required")

check("wrong old password is refused", client.post("/auth/change-password", headers=headers(sam_token), json={"current_password": "nope-nope-123", "new_password": "My-Own-Pass-77"}).status_code == 400)
check("weak new password is refused", client.post("/auth/change-password", headers=headers(sam_token), json={"current_password": "Temp-Pass-2026", "new_password": "abc"}).status_code == 400)
changed = client.post("/auth/change-password", headers=headers(sam_token), json={"current_password": "Temp-Pass-2026", "new_password": "My-Own-Pass-77"})
check("they can set their own password", changed.status_code == 200)
check("the old session stops working", client.get("/auth/me", headers=headers(sam_token)).status_code == 401)
check("the old password stops working", login("sam", "Temp-Pass-2026").status_code == 401)
sam_token = changed.json()["access_token"]
check("the new session works", client.get("/auth/me", headers=headers(sam_token)).status_code == 200)
check("a viewer cannot use admin tools", client.get("/admin/users", headers=headers(sam_token)).status_code == 403)

sam_id = made.json()["id"]
check("admin can reset a forgotten password", client.post(f"/admin/users/{sam_id}/reset-password", headers=headers(admin_token), json={"new_password": "Reset-Pass-2026"}).status_code == 200)
check("reset logs the person out", client.get("/auth/me", headers=headers(sam_token)).status_code == 401)
again = login("sam", "Reset-Pass-2026")
check("they must choose a new password again", again.json()["must_change_password"] is True)

boss_id = users.get_by_username("boss")["id"]
check("admin cannot switch themselves off", client.patch(f"/admin/users/{boss_id}", headers=headers(admin_token), json={"is_active": False}).status_code == 400)
check("admin can switch another person off", client.patch(f"/admin/users/{sam_id}", headers=headers(admin_token), json={"is_active": False}).status_code == 200)
check("a switched-off person cannot log in", login("sam", "Reset-Pass-2026").status_code == 401)

for _ in range(5):
    login("boss", "wrong-password-1")
locked = login("boss", "Strong-Pass-123")
check("5 wrong tries lock the account", locked.status_code == 429)

trail = users.list_audit(100)
check("everything was written in the audit trail", len(trail) > 8)
print()
print(passed, "passed,", failed, "failed")