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
