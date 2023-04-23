from django.urls import path, include
from rest_framework.routers import SimpleRouter

from core.views import TaskViewSet

router = SimpleRouter()
router.register("tasks", TaskViewSet, basename="tasks")

urlpatterns = [
    path("", include(router.urls)),
]
