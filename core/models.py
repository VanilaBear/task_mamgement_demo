import logging
import uuid
from typing import Tuple

from django.contrib.auth.models import User
from django.db import models
from django.utils.timezone import now

from core.constants import (
    STATUS_CHOICES,
    STATUS_PENDING,
    STATUS_IN_PROGRESS,
    STATUS_COMPLETED,
    STATUS_RETRY_PENDING,
    STATUS_CANCELED,
    STATUS_FAILED,
)
from core.exceptions import TaskException

logger = logging.getLogger(__name__)


class TaskMeta(models.Model):
    """TaskMeta entity model"""

    id = models.UUIDField("Task ID", primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    finished_at = models.DateTimeField(null=True)
    result = models.CharField(max_length=255)

    name = models.CharField(max_length=36)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    available_statuses_map = {
        STATUS_PENDING: (STATUS_IN_PROGRESS, STATUS_CANCELED),
        STATUS_IN_PROGRESS: (
            STATUS_IN_PROGRESS,
            STATUS_FAILED,
            STATUS_RETRY_PENDING,
            STATUS_COMPLETED,
            STATUS_CANCELED,
        ),
        STATUS_RETRY_PENDING: (STATUS_IN_PROGRESS, STATUS_CANCELED),
    }

    class Meta:
        """Metadata for the TaskMeta model"""

        ordering = ["name"]

    def __str__(self) -> str:
        """String for representing the TaskMeta object."""
        return f"{self.name} {self.id}"

    def start(self):
        self.change_status(STATUS_IN_PROGRESS)
        self.save()

    def change_status(self, status: str):
        self.validate_next_status(status)
        self.status = status

    def validate_next_status(self, status):
        if status not in self.next_available_statuses:
            raise TaskException(f"Can not change status from {self.status} to {status} for the task {self.id}.")

    def finish(self, status):
        self.change_status(status)
        self.finished_at = now()
        self.result = "Some task's result might be here"
        self.save()

    def add_error(self, message: str, traceback: str):
        """Stores related error information"""
        TaskError.objects.create(task_id=self.id, message=message, traceback=traceback)

    @property
    def is_in_progress(self) -> bool:
        return self.status == STATUS_IN_PROGRESS

    @property
    def next_available_statuses(self) -> Tuple[str, ...]:
        return self.available_statuses_map.get(self.status, ())


class TaskError(models.Model):
    """TaskError entity model"""

    task = models.ForeignKey(TaskMeta, on_delete=models.CASCADE, related_name="errors")
    message = models.CharField(max_length=255)
    traceback = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Metadata for the TaskError model"""

        ordering = ["id"]
