from datetime import timedelta

from django.test import override_settings, TestCase
from django.utils.timezone import now
from freezegun import freeze_time
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APITestCase

from authentication.backends import ExpiringTokenAuthentication
from authentication.tests.factories import UserFactory, TokenFactory
from authentication.views import CustomAuthToken


class CustomAuthTokenTest(APITestCase):
    """Test cases for the CustomAuthToken View"""

    def setUp(self):
        self.password = "test_password"
        self.user = UserFactory(password=self.password)

    @freeze_time("2023-04-26 18:17:16")
    def test_refresh_token(self):
        """Tests the refresh_token method"""

        token = TokenFactory(user=self.user)
        refreshed_token = CustomAuthToken.refresh_token(self.user)
        self.assertFalse(Token.objects.filter(pk=token.pk).exists())
        self.assertTrue(Token.objects.filter(pk=refreshed_token.pk).exists())
        self.assertNotEqual(token.key, refreshed_token.key)
        self.assertEqual(refreshed_token.user, self.user)
        self.assertEqual(refreshed_token.created, now())

    def test_post(self):
        """Tests the post method"""

        url = "/auth/token/"
        data = {"username": self.user.username, "password": self.password}
        response = self.client.post(url, data=data)

        self.assertIn("token", response.data)
        token_key = response.data["token"]

        token = Token.objects.get(key=token_key)
        self.assertTrue(token.user.is_authenticated)
        self.assertEqual(token.user, self.user)


class ExpiringTokenAuthenticationTest(TestCase):
    """Test cases for the ExpiringTokenAuthentication backend"""

    @freeze_time("2023-04-25 00:00:00")
    def setUp(self):
        self.user = UserFactory()
        self.token = TokenFactory(user=self.user, created=now() - timedelta(days=3))

    @freeze_time("2023-04-26 00:00:00")
    @override_settings(TOKEN_EXPIRATION_TIME=86400)
    def test_authenticate_credentials_valid_token(self):
        """Tests the authenticate_credentials method with a valid token"""

        result = ExpiringTokenAuthentication().authenticate_credentials(self.token.key)
        self.assertEqual(result, (self.user, self.token))

    @freeze_time("2023-04-26 00:00:00")
    @override_settings(TOKEN_EXPIRATION_TIME=86399)
    def test_authenticate_credentials_expired_token(self):
        """Tests the authenticate_credentials method with an expired token"""

        with self.assertRaises(AuthenticationFailed):
            ExpiringTokenAuthentication().authenticate_credentials(self.token.key)
