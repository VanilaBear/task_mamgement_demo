from django.contrib import admin
from django.contrib.auth.views import LogoutView, LoginView
from django.urls import path, include
from django.views.generic import TemplateView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework.authentication import SessionAuthentication, BasicAuthentication


schema_view = get_schema_view(
    openapi.Info(
        title="Swagger API",
        default_version="v1",
        description="API for Task management system [demo]",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="alex.n.ermoalev@gmail.com"),
        license=openapi.License(name="Absolutely free License"),
    ),
    public=True,
    permission_classes=[permissions.IsAuthenticated],
    authentication_classes=[SessionAuthentication, BasicAuthentication],
)

urlpatterns = [
    path("", TemplateView.as_view(template_name="index.html"), name="index"),
    path("tasks/", TemplateView.as_view(template_name="tasks_list.html"), name="tasks_list"),
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    path("auth/", include("authentication.urls")),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
