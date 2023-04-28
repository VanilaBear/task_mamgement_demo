from rest_framework import serializers

from core.constants import (
    STATUS_CANCELED,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_RETRY_PENDING,
)
from core.models import TaskError, TaskMeta


class TaskErrorSerializer(serializers.ModelSerializer):
    """Serializer for TaskError model instances"""

    class Meta:
        model = TaskError
        fields = ["message", "created_at"]


class TaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Task model instances"""

    uuid = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = TaskMeta
        fields = ["uuid", "name"]


class TaskSerializer(TaskCreateSerializer):
    """Serializer for Task model instances"""

    errors = TaskErrorSerializer(many=True, read_only=True)
    user = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = TaskMeta
        fields = ["uuid", "name", "created_at", "finished_at", "status", "result", "errors", "user"]

    def to_representation(self, instance):
        """Custom representation for TaskMeta model instances that remove data depending on status"""

        data = super().to_representation(instance)
        if instance.status != STATUS_COMPLETED:
            data.pop("result", None)
        if instance.status not in [STATUS_COMPLETED, STATUS_FAILED, STATUS_CANCELED, STATUS_RETRY_PENDING]:
            data.pop("finished_at", None)
        if instance.status not in [STATUS_FAILED, STATUS_RETRY_PENDING]:
            data.pop("errors", None)
        return data


class TaskOptionsSerializer(serializers.Serializer):
    """Serializer for validating task options"""

    countdown = serializers.IntegerField(min_value=0, required=False)
    max_retries = serializers.IntegerField(min_value=0, required=False)

    def to_internal_value(self, data):
        if "delay" in data:
            data["countdown"] = data.pop("delay")
        if "retry" in data:
            data["max_retries"] = data.pop("retry")
        return super().to_internal_value(data)


class TaskParametersSerializer(serializers.Serializer):
    """Serializer for validating task parameters"""

    param1 = serializers.IntegerField(min_value=0)
    param2 = serializers.CharField(required=False)


class TaskConfigurationSerializer(serializers.Serializer):
    """Serializer for validating task parameters"""

    params = TaskParametersSerializer()
    options = TaskOptionsSerializer()
