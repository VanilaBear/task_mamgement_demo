from django.urls import path

from authentication.views import CustomAuthToken

urlpatterns = [
    path("token/", CustomAuthToken.as_view()),
]
