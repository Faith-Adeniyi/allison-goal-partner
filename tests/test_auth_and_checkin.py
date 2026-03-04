import os
import unittest
import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.storage import PlanStorage


class AuthAndCheckinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.storage = PlanStorage()
        cls.created_plan_ids = []

    @classmethod
    def tearDownClass(cls):
        for plan_id in cls.created_plan_ids:
            file_path = os.path.join(cls.storage.base_dir, f"{plan_id}.json")
            if os.path.exists(file_path):
                os.remove(file_path)

    def _signup_and_login(self):
        unique = uuid.uuid4().hex[:10]
        email = f"user_{unique}@example.com"
        password = "StrongPass123"
        full_name = f"User {unique}"

        signup_resp = self.client.post(
            "/auth/signup",
            json={"full_name": full_name, "email": email, "password": password},
        )
        self.assertEqual(signup_resp.status_code, 200)
        signup_data = signup_resp.json()

        login_resp = self.client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        self.assertEqual(login_resp.status_code, 200)
        login_data = login_resp.json()

        return signup_data, login_data

    def test_signup_and_login_return_jwt(self):
        _, login_data = self._signup_and_login()
        self.assertIn("access_token", login_data)
        self.assertEqual(login_data.get("token_type"), "bearer")
        self.assertIn("user", login_data)
        self.assertIn("id", login_data["user"])

    def test_goals_requires_auth(self):
        response = self.client.get("/goals")
        self.assertEqual(response.status_code, 401)

    def test_user_goal_isolated(self):
        _, login_data_a = self._signup_and_login()
        token_a = login_data_a["access_token"]
        user_a_id = login_data_a["user"]["id"]

        plan_payload = {
            "goal_summary": "Isolation test goal",
            "target_date": "2030-01-01",
            "weekly_structure_suggestion": "Do one task per day.",
            "milestones": [
                {
                    "id": 1,
                    "title": "Milestone 1",
                    "tasks": [{"id": 1, "title": "Task 1", "is_completed": 0}],
                    "is_completed": 0,
                }
            ],
            "category": "General",
        }
        plan_id = self.storage.save_plan(plan_payload, owner_user_id=user_a_id)
        self.created_plan_ids.append(plan_id)

        headers_a = {"Authorization": f"Bearer {token_a}"}
        goals_a = self.client.get("/goals", headers=headers_a)
        self.assertEqual(goals_a.status_code, 200)
        goal_ids_a = {goal["plan_id"] for goal in goals_a.json().get("data", [])}
        self.assertIn(plan_id, goal_ids_a)

        _, login_data_b = self._signup_and_login()
        token_b = login_data_b["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}
        goals_b = self.client.get("/goals", headers=headers_b)
        self.assertEqual(goals_b.status_code, 200)
        goal_ids_b = {goal["plan_id"] for goal in goals_b.json().get("data", [])}
        self.assertNotIn(plan_id, goal_ids_b)

    def test_checkin_persists(self):
        _, login_data = self._signup_and_login()
        token = login_data["access_token"]
        user_id = login_data["user"]["id"]

        plan_payload = {
            "goal_summary": "Check-in goal",
            "target_date": "2030-01-01",
            "weekly_structure_suggestion": "Stay consistent daily.",
            "milestones": [
                {
                    "id": 1,
                    "title": "Milestone 1",
                    "tasks": [{"id": 1, "title": "Task 1", "is_completed": 0}],
                    "is_completed": 0,
                }
            ],
        }
        plan_id = self.storage.save_plan(plan_payload, owner_user_id=user_id)
        self.created_plan_ids.append(plan_id)

        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.post(
            f"/goals/{plan_id}/checkin",
            headers=headers,
            json={
                "worked_today": True,
                "notes": "Completed one step.",
                "blockers": "",
                "energy_level": "steady",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body.get("status"), "success")
        self.assertEqual(body.get("plan_id"), plan_id)

        saved = self.storage.load_plan(plan_id, owner_user_id=user_id)
        self.assertIsNotNone(saved)
        self.assertIn("checkins", saved)
        self.assertGreaterEqual(len(saved["checkins"]), 1)


if __name__ == "__main__":
    unittest.main()
