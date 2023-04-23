from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from core.tasks import sample_task, TaskConfig
from core.constants import STATUS_CANCELED
from core.models import TaskMeta
from core.permissions import TaskBasePermission, TaskCancelPermission
from core.serializers import TaskCreateSerializer, TaskSerializer, TaskConfigurationSerializer


class TaskViewSet(CreateModelMixin, RetrieveModelMixin, ListModelMixin, GenericViewSet):
    """A simple ModelViewSet for managing core"""

    serializer_class = TaskSerializer
    queryset = TaskMeta.objects.all()
    permission_classes = [IsAuthenticated, TaskBasePermission]

    def get_queryset(self):
        if self.request.user.is_staff:
            return self.queryset
        return TaskMeta.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        task_serializer = TaskCreateSerializer(data=request.data)
        task_serializer.is_valid(raise_exception=True)

        configuration_serializer = TaskConfigurationSerializer(data=request.data)
        configuration_serializer.is_valid(raise_exception=True)
        options = configuration_serializer.data["options"]
        parameters = configuration_serializer.data["params"]

        task_id = str(self.perform_create(task_serializer).id)

        sample_task.apply_async(kwargs={"task_id": task_id, **parameters, **options}, task_id=task_id)

        headers = self.get_success_headers(task_serializer.data)
        return Response(task_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["POST"], permission_classes=[IsAuthenticated, TaskCancelPermission])
    def cancel(self, request, *args, **kwargs):
        try:
            task = self.get_object()
            task.finish(STATUS_CANCELED)
        except Exception as error:
            pass
