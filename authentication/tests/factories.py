import factory
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.authtoken.models import Token


class UserFactory(factory.django.DjangoModelFactory):
    """User model factory"""

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    username = factory.Faker("user_name")
    email = factory.Faker("email")
    password = factory.PostGenerationMethodCall("set_password", "adm1n")

    class Meta:
        model = User


class TokenFactory(factory.django.DjangoModelFactory):
    """Token model factory"""

    key = factory.LazyAttribute(lambda _: Token.generate_key())
    user = factory.SubFactory(UserFactory)
    created = timezone.now()

    class Meta:
        model = Token
