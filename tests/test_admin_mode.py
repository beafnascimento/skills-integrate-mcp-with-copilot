import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import src.app as app_module
import src.create_teacher as teacher_cli


class AdminModeTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.credentials_file = Path(self.temporary_directory.name) / "teachers.json"
        salt, password_hash = app_module.hash_password("correct-password")
        self.credentials_file.write_text(
            json.dumps(
                [
                    {
                        "username": "teacher",
                        "salt": salt,
                        "password_hash": password_hash,
                    }
                ]
            ),
            encoding="utf-8",
        )
        self.original_credentials_file = app_module.TEACHERS_FILE
        self.original_activities = app_module.activities
        app_module.TEACHERS_FILE = self.credentials_file
        app_module.activities = copy.deepcopy(self.original_activities)
        self.client = TestClient(app_module.app)

    def tearDown(self):
        self.client.close()
        app_module.TEACHERS_FILE = self.original_credentials_file
        app_module.activities = self.original_activities
        self.temporary_directory.cleanup()

    def test_students_can_view_activities_but_cannot_change_registrations(self):
        self.assertEqual(self.client.get("/activities").status_code, 200)

        signup = self.client.post(
            "/activities/Chess Club/signup",
            params={"email": "student@mergington.edu"},
        )
        unregister = self.client.delete(
            "/activities/Chess Club/unregister",
            params={"email": "michael@mergington.edu"},
        )

        self.assertEqual(signup.status_code, 401)
        self.assertEqual(unregister.status_code, 401)

    def test_teacher_login_authorizes_registration_and_unregistration(self):
        login = self.client.post(
            "/auth/login",
            json={"username": "teacher", "password": "correct-password"},
        )

        self.assertEqual(login.status_code, 200)
        self.assertIn("httponly", login.headers["set-cookie"].lower())

        signup = self.client.post(
            "/activities/Chess Club/signup",
            params={"email": "student@mergington.edu"},
        )
        unregister = self.client.delete(
            "/activities/Chess Club/unregister",
            params={"email": "michael@mergington.edu"},
        )

        self.assertEqual(signup.status_code, 200)
        self.assertEqual(unregister.status_code, 200)

    def test_invalid_teacher_password_is_rejected(self):
        response = self.client.post(
            "/auth/login",
            json={"username": "teacher", "password": "incorrect-password"},
        )

        self.assertEqual(response.status_code, 401)

    def test_logout_removes_mutation_access(self):
        self.client.post(
            "/auth/login",
            json={"username": "teacher", "password": "correct-password"},
        )
        logout = self.client.post("/auth/logout")
        signup = self.client.post(
            "/activities/Chess Club/signup",
            params={"email": "student@mergington.edu"},
        )

        self.assertEqual(logout.status_code, 200)
        self.assertEqual(signup.status_code, 401)

    def test_teacher_setup_stores_a_hash_with_private_file_permissions(self):
        with (
            patch.object(teacher_cli, "TEACHERS_FILE", self.credentials_file),
            patch("builtins.input", return_value="new-teacher"),
            patch("getpass.getpass", side_effect=["strong-secret", "strong-secret"]),
        ):
            teacher_cli.main()

        contents = self.credentials_file.read_text(encoding="utf-8")
        self.assertNotIn("strong-secret", contents)
        self.assertTrue(app_module.is_valid_teacher("new-teacher", "strong-secret"))
        self.assertEqual(self.credentials_file.stat().st_mode & 0o777, 0o600)
