from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from django.utils.timezone import now
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase

from authentication.tests.factories import UserFactory
from core.constants import (
    STATUS_IN_PROGRESS,
    STATUS_COMPLETED,
    STATUS_CANCELED,
    STATUS_FAILED,
    STATUS_RETRY_PENDING,
    STATUS_PENDING,
)
from core.exceptions import TaskException
from core.models import TaskError, TaskMeta
from core.tests.factories import TaskMetaFactory, TaskErrorFactory


class TaskMetaTest(TestCase):
    """Test cases for the TaskMeta model"""

    def setUp(self):
        self.task = TaskMetaFactory()

    def test_string_representation(self):
        """Tests string representation of the TaskMeta object"""
        self.assertEqual(str(self.task), f"{self.task.name} {self.task.id}")

    def test_start(self):
        """Tests the start method"""
        self.task.start()
        self.assertEqual(self.task.status, STATUS_IN_PROGRESS)

    def test_change_status(self):
        """Tests the change_status method"""

        self.task.change_status(STATUS_IN_PROGRESS)
        self.assertEqual(self.task.status, STATUS_IN_PROGRESS)

    def test_status_change_exception(self):
        """Tests the change_status method in case of exceptions"""
        new_status = "NON_EXISTENT_OR_UNAVAILABLE_STATUS"
        with self.assertRaises(TaskException):
            self.task.change_status(new_status)

    @freeze_time("2023-04-26 18:17:16")
    def test_finish(self):
        """Tests the finish method"""
        task = TaskMetaFactory(status=STATUS_IN_PROGRESS)
        task.finish(STATUS_COMPLETED)
        self.assertEqual(task.finished_at, timezone.now())
        self.assertEqual(task.status, STATUS_COMPLETED)
        self.assertEqual(task.result, "Some task's result might be here")

    def test_add_error(self):
        """Tests the add_error method"""
        message = "Error message"
        traceback = "Traceback"
        self.task.add_error(message, traceback)
        error = TaskError.objects.filter(message=message, traceback=traceback, task_id=self.task.id).first()
        self.assertIsNotNone(error)
        self.assertEqual(self.task.errors.count(), 1)

    def test_is_in_progress(self):
        """Tests the is_in_progress property"""
        self.assertFalse(self.task.is_in_progress)
        self.task.status = STATUS_IN_PROGRESS
        self.task.save()
        self.assertTrue(self.task.is_in_progress)

    def test_next_available_statuses(self):
        """Tests the next_available_statuses property"""
        self.assertEqual(self.task.next_available_statuses, (STATUS_IN_PROGRESS, STATUS_CANCELED))

        self.task.status = STATUS_IN_PROGRESS
        self.assertTupleEqual(
            self.task.next_available_statuses,
            (
                STATUS_IN_PROGRESS,
                STATUS_FAILED,
                STATUS_RETRY_PENDING,
                STATUS_COMPLETED,
                STATUS_CANCELED,
            ),
        )

        self.task.status = STATUS_RETRY_PENDING
        self.assertTupleEqual(self.task.next_available_statuses, (STATUS_IN_PROGRESS, STATUS_CANCELED))

        self.task.status = STATUS_FAILED
        self.assertTupleEqual(self.task.next_available_statuses, ())

        self.task.status = STATUS_COMPLETED
        self.assertTupleEqual(self.task.next_available_statuses, ())

        self.task.status = STATUS_CANCELED
        self.assertTupleEqual(self.task.next_available_statuses, ())


@override_settings(CELERY_ALWAYS_EAGER=True)
class TaskViewSetTest(APITestCase):
    """Test cases for the TaskViewSet class"""

    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.url = "/api/tasks/"
        self.data = {
            "name": "task_name_test",
            "options": {"delay": 100, "retry": 2},
            "params": {"param1": 10, "param2": "param2"},
        }
        self.task = TaskMetaFactory(user=self.user)

    @staticmethod
    def get_expected_data(task) -> dict:
        expected_data = dict(
            uuid=str(task.id),
            name=task.name,
            created_at=task.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            status=task.status,
            user=task.user.username,
        )
        if task.status in (STATUS_COMPLETED, STATUS_FAILED, STATUS_RETRY_PENDING, STATUS_CANCELED):
            expected_data["finished_at"] = task.finished_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        if task.status == STATUS_COMPLETED:
            expected_data["result"] = task.result
        if task.status in (STATUS_FAILED, STATUS_RETRY_PENDING):
            expected_data["errors"] = [
                {"message": error.message, "created_at": error.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")}
                for error in task.errors.all()
            ]

        return expected_data

    @patch("core.tasks.sample_task.apply_async")
    def test_create_task_success(self, mock_task_apply_async):
        """Tests the create method"""
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        task = TaskMeta.objects.filter(user=self.user, name=self.data["name"]).first()
        self.assertIsNotNone(task)

        mock_task_apply_async.assert_called_once_with(
            kwargs=dict(
                param1=self.data["params"]["param1"],
                param2=self.data["params"]["param2"],
                countdown=self.data["options"]["delay"],
                max_retries=self.data["options"]["retry"],
            ),
            task_id=str(task.id),
        )

    def test_retrieve_task(self):
        """Tests the retrieve method"""
        task_meta_common_kwargs = dict(user=self.user, finished_at=now(), result="result")
        pending_task = TaskMetaFactory(status=STATUS_PENDING, **task_meta_common_kwargs)
        in_progress_task = TaskMetaFactory(status=STATUS_IN_PROGRESS, **task_meta_common_kwargs)
        completed_task = TaskMetaFactory(status=STATUS_COMPLETED, **task_meta_common_kwargs)
        failed_task = TaskMetaFactory(status=STATUS_FAILED, **task_meta_common_kwargs)
        retry_pending_task = TaskMetaFactory(status=STATUS_RETRY_PENDING, **task_meta_common_kwargs)
        cancelled_task = TaskMetaFactory(status=STATUS_CANCELED, **task_meta_common_kwargs)
        TaskErrorFactory(task=failed_task)
        TaskErrorFactory(task=retry_pending_task)
        TaskErrorFactory(task=retry_pending_task)

        for task in (pending_task, in_progress_task, completed_task, failed_task, retry_pending_task, cancelled_task):
            with self.subTest(f"Tests the retrieve method for status {task.status}"):
                url = f"{self.url}{str(task.id)}/"
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertDictEqual(response.data, self.get_expected_data(task))
