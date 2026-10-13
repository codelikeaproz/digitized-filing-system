from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
from config.settings import frontend_api_path


class CookieAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="cookie-auth@test.local",
            password="Test@12345",
            role="admin",
            employee_number="109999",
            first_name="Cookie",
            last_name="Auth",
        )

    def login(self):
        return self.client.post(
            "/api/auth/login",
            {"email": self.user.email, "password": "Test@12345"},
            format="json",
        )

    def test_login_returns_access_token_and_sets_protected_refresh_cookie(self):
        response = self.login()

        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.data)
        self.assertNotIn("refresh", response.data)
        cookie = response.cookies[settings.AUTH_REFRESH_COOKIE_NAME]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], settings.AUTH_REFRESH_COOKIE_SAMESITE)
        self.assertEqual(cookie["path"], settings.AUTH_REFRESH_COOKIE_PATH)

    @override_settings(AUTH_REFRESH_COOKIE_SECURE=True, AUTH_REFRESH_COOKIE_PATH="/digifile/api/")
    def test_production_cookie_is_secure_and_supports_subpath_deployment(self):
        response = self.login()

        cookie = response.cookies[settings.AUTH_REFRESH_COOKIE_NAME]
        self.assertTrue(cookie["secure"])
        self.assertEqual(cookie["path"], "/digifile/api/")
        self.assertEqual(frontend_api_path("https://apps.cmu.edu.ph/digifile"), "/digifile/api/")

    def test_refresh_reads_cookie_and_rejects_request_body_token(self):
        login_response = self.login()
        refresh = login_response.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value

        response = self.client.post("/api/token/refresh/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

        client_without_cookie = APIClient()
        response = client_without_cookie.post(
            "/api/token/refresh/",
            {"refresh": refresh},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_logout_clears_refresh_cookie(self):
        self.login()

        response = self.client.post("/api/auth/logout", {}, format="json")

        self.assertEqual(response.status_code, 200)
        cookie = response.cookies[settings.AUTH_REFRESH_COOKIE_NAME]
        self.assertEqual(cookie["max-age"], 0)

    def test_direct_token_pair_endpoint_is_not_exposed(self):
        response = self.client.post(
            "/api/token/",
            {"email": self.user.email, "password": "Test@12345"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
