from __future__ import annotations

import base64
import io
import json
import os
from pathlib import Path

import pandas as pd
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse


class MailAutomationIntegrationTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.password = "testpass123"
        self.user = User.objects.create_user(username="tester", password=self.password)

    def test_redirects_to_login_when_unauthenticated(self) -> None:
        url = reverse("automation:mail_automation")
        response = self.client.get(url)
        # Django appends next param
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/?next=", response.headers.get("Location", ""))

    def test_page_loads_after_login(self) -> None:
        login_ok = self.client.login(username="tester", password=self.password)
        self.assertTrue(login_ok)
        url = reverse("automation:mail_automation")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mail Automation")

    def _make_excel_file(self, rows: list[dict[str, object]]) -> io.BytesIO:
        df = pd.DataFrame(rows)
        buff = io.BytesIO()
        with pd.ExcelWriter(buff, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        buff.seek(0)
        return buff

    @override_settings(EMAIL_TEMPLATES_PATH=str(Path.cwd() / "test_email_templates.json"))
    def test_dry_run_with_sample_excel_shows_preview_and_logs(self) -> None:
        # Prepare template file
        tpl_path = Path(os.environ.get("EMAIL_TEMPLATES_PATH", "test_email_templates.json"))
        templates = {
            "Welcome": {
                "subject": "Hello {name}",
                "body": "Dear {name}, your score is {score}.",
            }
        }
        with open(tpl_path, "w", encoding="utf-8") as f:
            json.dump(templates, f)

        try:
            self.client.login(username="tester", password=self.password)
            url = reverse("automation:mail_automation")

            excel = self._make_excel_file([
                {"email": "a@example.com", "name": "Alice", "score": 95},
                {"email": "b@example.com", "name": "Bob", "score": 88},
            ])

            # Step 1: POST form for preview
            response = self.client.post(
                url,
                data={
                    "excel_file": excel,
                    "template": "Welcome",
                    "subject": "",  # allow form to use template subject
                    "dry_run": "on",
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Preview (first 20 rows)")
            self.assertContains(response, "a@example.com")
            self.assertContains(response, "b@example.com")

            # Step 2: confirm send (still dry run)
            response = self.client.post(
                url,
                data={
                    "template": "Welcome",
                    "subject": "Hello {name}",
                    "dry_run": "on",
                    "confirm_send": "1",
                },
            )
            self.assertEqual(response.status_code, 200)
            # Shows logs header and dry lines
            self.assertContains(response, "Logs")
            self.assertContains(response, "[DRY] a@example.com")
            self.assertContains(response, "[DRY] b@example.com")
        finally:
            if tpl_path.exists():
                tpl_path.unlink()

    @override_settings(EMAIL_TEMPLATES_PATH=str(Path.cwd() / "test_email_templates.json"))
    def test_placeholder_rendering_in_preview_sample(self) -> None:
        # Prepare a template using placeholders
        tpl_path = Path(os.environ.get("EMAIL_TEMPLATES_PATH", "test_email_templates.json"))
        templates = {
            "Sample": {
                "subject": "Hi {name}",
                "body": "Dear {name}, your id is {id} and email {email}.",
            }
        }
        with open(tpl_path, "w", encoding="utf-8") as f:
            json.dump(templates, f)

        try:
            self.client.login(username="tester", password=self.password)
            url = reverse("automation:mail_automation")

            excel = self._make_excel_file([
                {"email": "x@example.com", "name": "Xena", "id": 42},
            ])

            response = self.client.post(
                url,
                data={
                    "excel_file": excel,
                    "template": "Sample",
                    "subject": "",  # let template subject prefill
                    "dry_run": "on",
                },
            )

            self.assertEqual(response.status_code, 200)
            # Verify rendered sample body content included
            self.assertContains(response, "Rendered sample (row 1)")
            self.assertContains(response, "Dear Xena, your id is 42 and email x@example.com.")
        finally:
            if tpl_path.exists():
                tpl_path.unlink()



