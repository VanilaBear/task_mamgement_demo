from rest_framework import serializers

from tasks.constants import STATUS_COMPLETED, STATUS_FAILED, STATUS_RETRY_PENDING, STATUS_CANCELLED
from tasks.models import Task, TaskError


class TaskErrorSerializer(serializers.ModelSerializer):
    """Serializer for TaskError model instances"""

    class Meta:
        model = TaskError
        fields = ["message", "traceback", "created_at"]


class TaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Task model instances"""

    uuid = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = Task
        fields = ["uuid", "name"]


class TaskSerializer(TaskCreateSerializer):
    """Serializer for Task model instances"""

    errors = TaskErrorSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = ["uuid", "name", "created_at", "finished_at", "status", "result", "errors"]
        read_only_fields = ["uuid", "name", "created_at", "finished_at", "status", "result", "errors"]

    def to_representation(self, instance):
        """Custom representation for Task model instances that remove data depending on status"""
        data = super().to_representation(instance)
        if instance.status != STATUS_COMPLETED:
            data.pop("result", None)
        if instance.status not in [STATUS_COMPLETED, STATUS_COMPLETED, STATUS_CANCELLED]:
            data.pop("finished_at", None)
        if instance.status not in [STATUS_FAILED, STATUS_RETRY_PENDING]:
            data.pop("errors", None)
        return data
