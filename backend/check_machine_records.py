from datetime import datetime, timedelta, timezone
import unittest

import check_registry as registry
from app import ai, bench, db, forecast, users


class MachineRecordTests(unittest.TestCase):
    def setUp(self):
        setup = registry.RegistryTests()
        setup.setUp()
        self.api = setup.client
        self.admin = setup.headers
        body = setup.machine()
        self.mid = setup.post("/machines",body).json()["id"]
        self.path = "/equipment/" + body["machine_id"]
        login = self.api.post("/auth/login",json={"username":"viewer","password":"Testing-Pass-123"})
        self.viewer = {"Authorization":"Bearer "+login.json()["access_token"]}
        self.engineer = body["engineer_id"]
        self.uid = users.get_by_username("viewer")["id"]

    def test_resources_permissions_and_guidance(self):
        self.assertEqual(self.api.get("/equipment",headers=self.viewer).status_code,200)
        self.assertFalse(self.api.get(self.path,headers=self.viewer).json()["can_edit"])
        url = self.path+"/manuals/user"
        self.assertEqual(self.api.get(url,headers=self.viewer).status_code,403)
        with db.connect() as conn:
            conn.execute("INSERT INTO engineer_accounts VALUES(?,?)",(self.engineer,self.uid))
        record = {"serviced":"2026-01-04","due":"2026-02-04","symptom":"High temperature","outcome":"Cleaned cooling inlet"}
        self.assertEqual(self.api.post(self.path+"/services",headers=self.viewer,json=record).status_code,200)
        self.assertEqual(self.api.put(url,params={"name":"motor.pdf","excerpt":"Inspect cooling inlet, page 4."},content=b"%PDF-test",headers=self.admin).status_code,200)
        self.assertEqual(self.api.get(url,headers=self.viewer).content,b"%PDF-test")
        notes=dict(description="Bench motor",probe_location="Housing",operating_load="Idle",approved_range="Awaiting reference")
        self.assertEqual(self.api.put(self.path+"/notes",headers=self.viewer,json=notes).status_code,200)
        saved=self.api.get(self.path,headers=self.admin).json()
        self.assertEqual(saved["edits"][0]["editor"],"viewer")
        answer=self.api.post(self.path+"/guidance",headers=self.viewer,json={"question":"temperature cooling service"}).json()
        self.assertIn("Cleaned cooling inlet",answer["answer"])
        self.assertIn("motor.pdf (engineer-entered extract)",answer["sources"])
        with db.connect() as conn:
            conn.execute("UPDATE machines SET engineer_id=NULL WHERE id=?",(self.mid,))
        self.assertNotIn("services",self.api.get(self.path,headers=self.viewer).json())
        self.assertEqual(self.api.post(self.path+"/services",headers=self.viewer,json=record).status_code,403)
        self.assertEqual(self.api.get(url,headers=self.viewer).status_code,403)

    def test_forecast_and_isolated_demo(self):
        self.assertGreater(ai._trend(list(range(10)),list(range(10)))[1],6)
        start=datetime.now(timezone.utc)
        with db.connect() as conn:
            for i in range(101):
                stamp=(start+timedelta(seconds=i*10)).isoformat()
                temp=25+i/10
                conn.execute("INSERT INTO bench_samples(registry_id,received_at,sample) VALUES(?,?,?)",(self.mid,stamp,bench.BenchSample(probe_c=temp).model_dump_json()))
                forecast.update(conn,self.mid,stamp,temp,30)
            prediction=conn.execute("SELECT * FROM motor_forecasts WHERE registry_id=? ORDER BY id LIMIT 1",(self.mid,)).fetchone()
            self.assertEqual((prediction["predicted"],prediction["actual"],prediction["result"]),(1,1,"crossed"))
        self.assertEqual(self.api.post("/simulator/reset").status_code,401)
        self.assertEqual(self.api.post("/simulator/load",headers=self.viewer).status_code,403)
        self.assertEqual(self.api.post("/simulator/load",headers=self.admin).status_code,200)
        self.assertEqual(self.api.get("/simulator/analysis",headers=self.admin).json()["source"],"simulated")
        self.assertEqual(self.api.post("/simulator/reset",headers=self.admin).status_code,200)
        self.assertEqual(bench.latest("compressor-1")["probe_c"],35)


if __name__ == "__main__":
    unittest.main()

