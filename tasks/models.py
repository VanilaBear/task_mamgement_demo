import uuid

from django.contrib.auth.models import User
from django.db import models

from tasks.constants import STATUS_CHOICES, STATUS_PENDING


class Task(models.Model):
    """Task entity model"""

    id = models.UUIDField("Unique Task ID", primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    finished_at = models.DateTimeField(null=True)
    result = models.CharField(max_length=255)

    name = models.CharField(max_length=36)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    class Meta:
        """Metadata for the Task model"""

        ordering = ["name"]

    def __str__(self) -> str:
        """String for representing the Task object."""
        return f"{self.name} {self.id}"


class TaskError(models.Model):
    """TaskError entity model"""

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="errors")
    message = models.CharField(max_length=255)
    traceback = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Metadata for the TaskError model"""

        ordering = ["id"]
