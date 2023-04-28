from celery.result import AsyncResult
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from core.constants import STATUS_CANCELED
from core.exceptions import TaskException
from core.models import TaskMeta
from core.permissions import TaskBasePermission, TaskCancelPermission
from core.serializers import (
    TaskConfigurationSerializer,
    TaskCreateSerializer,
    TaskSerializer,
)
from core.swagger_schemas import (
    CANCEL_TASK_RESPONSES,
    CREATE_TASK_REQUEST_BODY,
    CREATE_TASK_RESPONSES,
)
from core.tasks import sample_task


class TaskViewSet(CreateModelMixin, RetrieveModelMixin, ListModelMixin, GenericViewSet):
    """Task Management API View Set"""

    serializer_class = TaskSerializer
    queryset = TaskMeta.objects.all()
    permission_classes = [IsAuthenticated, TaskBasePermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["name"]
    search_fields = ["name"]
    ordering_fields = ["name"]

    def get_queryset(self):
        if self.request.user.is_staff:
            return self.queryset
        return TaskMeta.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)

    @swagger_auto_schema(request_body=CREATE_TASK_REQUEST_BODY, responses=CREATE_TASK_RESPONSES)
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        task_serializer = TaskCreateSerializer(data=request.data)
        task_serializer.is_valid(raise_exception=True)

        configuration_serializer = TaskConfigurationSerializer(data=request.data)
        configuration_serializer.is_valid(raise_exception=True)
        options = configuration_serializer.data["options"]
        parameters = configuration_serializer.data["params"]

        task_id = str(self.perform_create(task_serializer).id)

        sample_task.apply_async(kwargs={**parameters, **options}, task_id=task_id)

        headers = self.get_success_headers(task_serializer.data)
        return Response(task_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @swagger_auto_schema(request_body=no_body, responses=CANCEL_TASK_RESPONSES)
    @action(detail=True, methods=["POST"], permission_classes=[IsAuthenticated, TaskCancelPermission])
    def cancel(self, request, *args, **kwargs):
        """Cancels task's execution"""

        task = self.get_object()
        try:
            result = AsyncResult(task.id)
            result.revoke()
            task.finish(STATUS_CANCELED)
            return Response({"message": f"Task {task.id} has been successfully canceled"}, status=status.HTTP_200_OK)
        except TaskException as error:
            return Response({"message": str(error)}, status=status.HTTP_409_CONFLICT)
