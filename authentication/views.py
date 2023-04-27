from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response


class CustomAuthToken(ObtainAuthToken):
    """Custom authentication view that generates and returns a token for a user"""

    @staticmethod
    def refresh_token(user: User) -> Token:
        """Creates a new token"""

        token, created = Token.objects.get_or_create(user=user)
        if not created:
            token.delete()
            token = Token.objects.create(user=user)
        return token

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token = self.refresh_token(user)

        return Response({"token": token.key})
