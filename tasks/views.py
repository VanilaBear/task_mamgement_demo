from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from tasks.models import Task
from tasks.permissions import TaskBasePermission, TaskStopPermission
from tasks.serializers import TaskCreateSerializer, TaskSerializer


class TaskViewSet(CreateModelMixin, RetrieveModelMixin, ListModelMixin, GenericViewSet):
    """A simple ModelViewSet for managing tasks"""

    serializer_class = TaskSerializer
    queryset = Task.objects.all()
    permission_classes = [IsAuthenticated, TaskBasePermission]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        self.serializer_class = TaskCreateSerializer
        response = super().create(request, *args, **kwargs)

        return response

    def get_queryset(self):
        if self.request.user.is_staff:
            return self.queryset
        return Task.objects.filter(user=self.request.user)

    @action(detail=True, methods=["POST"], permission_classes=[IsAuthenticated, TaskStopPermission])
    def cancel(self, request, *args, **kwargs):
        """Cancels tasks"""
        pass
