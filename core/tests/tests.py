import traceback
from unittest.mock import MagicMock, PropertyMock, patch

from django.test import TestCase, override_settings
from django.utils import timezone
from django.utils.timezone import now
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from authentication.tests.factories import UserFactory
from core.constants import (
    STATUS_CANCELED,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_IN_PROGRESS,
    STATUS_PENDING,
    STATUS_RETRY_PENDING,
)
from core.exceptions import TaskException
from core.models import TaskError, TaskMeta
from core.tasks import BaseSampleTask, sample_task
from core.tests.factories import TaskErrorFactory, TaskMetaFactory


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

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user_two = UserFactory()
        cls.user_admin = UserFactory(is_staff=True)

        client_admin = APIClient()
        client_admin.force_authenticate(user=cls.user_admin)
        # client_admin.login(username=cls.admin_user, password=cls.admin_user)
        cls.client_admin = client_admin

        client_user = APIClient()
        client_user.force_authenticate(user=cls.user)
        cls.client_user = client_user

        client_user_two = APIClient()
        client_user_two.force_authenticate(user=cls.user_two)
        cls.client_user_two = client_user_two

        cls.url = "/api/tasks/"
        cls.data = {
            "name": "task_name_test",
            "options": {"delay": 100, "retry": 2},
            "params": {"param1": 10, "param2": "param2"},
        }

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

        response = self.client_user.post(self.url, self.data, format="json")
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
                response = self.client_user.get(url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertDictEqual(response.data, self.get_expected_data(task))

    def test_retrieve_task_not_found(self):
        """Tests the retrieve method"""

        with self.subTest("Checks that there is no access to the task of another user"):
            task = TaskMetaFactory(user=self.user)
            url = f"{self.url}{str(task.id)}/"
            response = self.client_user_two.get(url)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        with self.subTest("Checks retrieve method for non-existent task id"):
            non_existent_task = TaskMetaFactory(user=self.user)
            non_existent_task.delete()
            url = f"{self.url}{str(non_existent_task.id)}/"
            response = self.client_user.get(url)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_tasks(self):
        """Tests the list method"""

        TaskMetaFactory(user=self.user)
        TaskMetaFactory(user=self.user)
        TaskMetaFactory(user=self.user_two)

        response = self.client_admin.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

        response = self.client_user.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        response = self.client_user_two.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    @patch("core.views.AsyncResult")
    def test_cancel_task(self, mock_async_result):
        """Tests the cancel method"""

        task = TaskMetaFactory(user=self.user)
        task_id = str(task.id)
        url = f"{self.url}{task_id}/cancel/"

        with self.subTest("Checks that there is no access to the task of another user"):
            response = self.client_user_two.post(url)
            task.refresh_from_db()
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertEqual(task.status, STATUS_PENDING)
            mock_async_result.assert_not_called()

        with self.subTest("Positive case"):
            mock_async_result.reset_mock()

            response = self.client_user.post(url)
            task.refresh_from_db()
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data, {"message": f"Task {task_id} has been successfully canceled"})
            self.assertEqual(task.status, STATUS_CANCELED)
            mock_async_result.assert_called_once_with(task.id)
            mock_async_result.return_value.revoke.assert_called_once()

        with self.subTest("Checks admin has access"):
            mock_async_result.reset_mock()
            task = TaskMetaFactory(user=self.user)
            task_id = str(task.id)
            url = f"{self.url}{task_id}/cancel/"

            response = self.client_admin.post(url)
            task.refresh_from_db()
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data, {"message": f"Task {task_id} has been successfully canceled"})
            self.assertEqual(task.status, STATUS_CANCELED)
            mock_async_result.assert_called_once_with(task.id)
            mock_async_result.return_value.revoke.assert_called_once()

        with self.subTest("Task has already been finished"):
            mock_async_result.reset_mock()
            task = TaskMetaFactory(user=self.user, status=STATUS_COMPLETED)
            url = f"{self.url}{str(task.id)}/cancel/"

            response = self.client_user.post(url)
            task.refresh_from_db()
            self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
            mock_async_result.assert_called_once_with(task.id)
            mock_async_result.return_value.revoke.assert_called_once()
            self.assertEqual(task.status, STATUS_COMPLETED)


class BaseSampleTaskTest(TestCase):
    """Test cases for the BaseSampleTask class"""

    def setUp(self):
        self.task_meta = TaskMetaFactory()
        self.sample_task = BaseSampleTask()
        self.sample_task.task_id = self.task_meta.id

    def test_get_task_meta(self):
        task_meta = self.sample_task._get_task_meta()
        self.assertEqual(task_meta, self.task_meta)

    @patch("celery.app.task.Task.request", new_callable=PropertyMock)
    def test_init_config(self, request_property_mock):
        request_mock = MagicMock()
        request_mock.id = self.task_meta.id
        request_property_mock.return_value = request_mock

        self.sample_task._init_config(countdown=120, max_retries=3)

        self.assertEqual(self.sample_task.countdown, 120)
        self.assertEqual(self.sample_task.max_retries, 3)
        self.assertEqual(self.sample_task.task_id, self.task_meta.id)

    @patch("core.tasks.logger")
    @patch("celery.app.task.Task.request", new_callable=PropertyMock)
    def test_log_attempt_number(self, request_property_mock, mock_logger):
        self.sample_task.request.retries = 0
        self.sample_task._log_attempt_number()
        mock_logger.info.assert_called_with("Attempt 1 of 1...")

        self.sample_task.request.retries = 1
        self.sample_task.max_retries = 2
        self.sample_task._log_attempt_number()
        mock_logger.warning.assert_called_with("Attempt 2 of 3...")

    @patch("core.tasks.BaseSampleTask.retry")
    @patch("core.tasks.BaseSampleTask._get_task_meta")
    @patch("core.tasks.logger")
    @patch("celery.app.task.Task.request", new_callable=PropertyMock)
    def test_handle_retry(self, request_property_mock, mock_logger, get_task_meta_mock, retry_mock):
        task_instance_mock = MagicMock()
        get_task_meta_mock.return_value = task_instance_mock

        with self.assertRaises(Exception):
            self.sample_task._handle_retry("Test error")
            traceback_msg = traceback.format_exc()

            mock_logger.warning.assert_called_once_with("Sending for retry ...")
            task_instance_mock.add_error.assert_called_once_with("Test error", traceback_msg)
            task_instance_mock.finish.assert_called_once_with(STATUS_RETRY_PENDING)
            retry_mock.assert_called_once()

    @patch("core.tasks.BaseSampleTask._get_task_meta")
    @patch("core.tasks.logger")
    @patch("celery.app.task.Task.request", new_callable=PropertyMock)
    def test_handle_failure(self, request_property_mock, mock_logger, get_task_meta_mock):
        task_instance_mock = MagicMock()
        get_task_meta_mock.return_value = task_instance_mock

        self.sample_task._handle_failure()

        task_instance_mock.finish.assert_called_once_with(STATUS_FAILED)
        mock_logger.error.assert_called_once_with(f"Failed to complete the task {self.task_meta.id}.")

    @patch("core.tasks.BaseSampleTask._get_task_meta")
    @patch("core.tasks.logger")
    @patch("time.sleep")
    @patch("celery.app.task.Task.request", new_callable=PropertyMock)
    def test_perform_task_successful(self, request_property_mock, sleep_mock, mock_logger, get_task_meta_mock):
        task_instance_mock = MagicMock()
        get_task_meta_mock.return_value = task_instance_mock

        self.sample_task._perform_task(1, "test_param2")

        task_instance_mock.start.assert_called_once()
        sleep_mock.assert_called_once_with(1)
        task_instance_mock.finish.assert_called_once_with(STATUS_COMPLETED)
        mock_logger.info.assert_called_once_with(f"The task {self.task_meta.id} has been successfully completed.")

    @patch("core.tasks.BaseSampleTask._get_task_meta")
    @patch("core.tasks.logger")
    @patch("time.sleep")
    @patch("celery.app.task.Task.request", new_callable=PropertyMock)
    def test_perform_task_exception_before(self, request_property_mock, sleep_mock, mock_logger, get_task_meta_mock):
        task_instance_mock = MagicMock()
        get_task_meta_mock.return_value = task_instance_mock

        with self.assertRaises(Exception):
            self.sample_task._perform_task(1, "raise exception before")
            task_instance_mock.start.assert_called_once()
            sleep_mock.assert_called_not_called()
            task_instance_mock.finish.assert_called_not_called()
            mock_logger.assert_called_not_called()

        with self.assertRaises(Exception):
            self.sample_task._perform_task(1, "raise exception after")
            task_instance_mock.start.assert_called_once()
            sleep_mock.assert_called_once_with(1)
            task_instance_mock.finish.assert_called_not_called()
            mock_logger.assert_called_not_called()


@override_settings(CELERY_ALWAYS_EAGER=True)
class TestSampleTask(TestCase):
    """Test cases for the sample_task celery task"""

    @classmethod
    def setUpTestData(cls):
        cls.task_args = (10, "test_param2")
        cls.task_kwargs = {"this": "is", "just": "test"}
        cls.task_id = "test_task_id"
        cls.info_log = f"Starting task execution [id: {cls.task_id}; param1: 10, param2: test_param2] ..."
        sample_task.task_id = cls.task_id

    @patch("core.tasks.sample_task._init_config")
    @patch("core.tasks.sample_task._log_attempt_number")
    @patch("core.tasks.sample_task._perform_task")
    @patch("core.tasks.sample_task._handle_retry")
    @patch("core.tasks.sample_task._handle_failure")
    @patch("core.tasks.logger")
    def test_sample_task_success(
        self,
        mock_logger,
        mock_handle_failure,
        mock_handle_retry,
        mock_perform_task,
        mock_log_attempt_number,
        mock_init_config,
    ):
        """Tests sample_task in positive case"""

        sample_task.apply(args=self.task_args, kwargs=self.task_kwargs).get()

        mock_init_config.assert_called_once_with(**self.task_kwargs)
        mock_logger.info.assert_called_once_with(self.info_log)
        mock_log_attempt_number.assert_called_once()
        mock_perform_task.assert_called_once_with(*self.task_args)

        mock_handle_retry.assert_not_called()
        mock_handle_failure.assert_not_called()

    @patch("core.tasks.sample_task._init_config")
    @patch("core.tasks.sample_task._log_attempt_number")
    @patch("core.tasks.sample_task._perform_task")
    @patch("core.tasks.sample_task._handle_retry")
    @patch("core.tasks.sample_task._handle_failure")
    @patch("core.tasks.logger")
    def test_sample_task_known_exception(
        self,
        mock_logger,
        mock_handle_failure,
        mock_handle_retry,
        mock_perform_task,
        mock_log_attempt_number,
        mock_init_config,
    ):
        """Tests sample_task in case of known exceptions"""

        with self.subTest("TaskMeta does not exist"):
            mock_perform_task.side_effect = TaskMeta.DoesNotExist

            sample_task.apply(args=self.task_args, kwargs=self.task_kwargs).get()

            mock_logger.info.assert_called_once_with(self.info_log)
            mock_init_config.assert_called_once_with(**self.task_kwargs)
            mock_perform_task.assert_called_once_with(*self.task_args)
            mock_logger.warning.assert_called_once_with(f"Task {self.task_id} not found")
            mock_handle_retry.assert_not_called()
            mock_handle_failure.assert_not_called()

        with self.subTest("Conflict - TaskException"):
            mock_perform_task.reset_mock()
            mock_init_config.reset_mock()
            mock_logger.reset_mock()
            mock_log_attempt_number.reset_mock()
            error_message = "is_error_message"
            mock_perform_task.side_effect = TaskException(error_message)

            sample_task.apply(args=self.task_args, kwargs=self.task_kwargs).get()

            mock_init_config.assert_called_once_with(**self.task_kwargs)
            mock_logger.info.assert_called_once_with(self.info_log)
            mock_log_attempt_number.assert_called_once()
            mock_perform_task.assert_called_once_with(*self.task_args)
            mock_logger.warning.assert_called_once_with(error_message)
            mock_handle_retry.assert_not_called()
            mock_handle_failure.assert_not_called()

    @patch("core.tasks.sample_task._init_config")
    @patch("core.tasks.sample_task._log_attempt_number")
    @patch("core.tasks.sample_task._perform_task")
    @patch("core.tasks.sample_task._handle_retry")
    @patch("core.tasks.sample_task._handle_failure")
    @patch("core.tasks.logger")
    def test_sample_task_unknown_exception(
        self,
        mock_logger,
        mock_handle_failure,
        mock_handle_retry,
        mock_perform_task,
        mock_log_attempt_number,
        mock_init_config,
    ):
        """Tests sample_task in case of unknown exceptions"""

        error_message = "error_message_123"
        mock_perform_task.side_effect = Exception(error_message)

        with self.subTest("No more retries"):
            sample_task.max_retries = 0
            sample_task.apply(args=self.task_args, kwargs=self.task_kwargs).get()

            mock_init_config.assert_called_once_with(**self.task_kwargs)
            mock_logger.info.assert_called_once_with(self.info_log)
            mock_log_attempt_number.assert_called_once()
            mock_perform_task.assert_called_once_with(*self.task_args)

            mock_handle_retry.assert_not_called()
            mock_handle_failure.assert_called_once()

        with self.subTest("One more retry"):
            sample_task.max_retries = 1
            mock_perform_task.reset_mock()
            mock_init_config.reset_mock()
            mock_logger.reset_mock()
            mock_log_attempt_number.reset_mock()
            mock_handle_failure.reset_mock()

            sample_task.apply(args=self.task_args, kwargs=self.task_kwargs).get()

            mock_init_config.assert_called_once_with(**self.task_kwargs)
            mock_logger.info.assert_called_once_with(self.info_log)
            mock_log_attempt_number.assert_called_once()
            mock_perform_task.assert_called_once_with(*self.task_args)

            mock_handle_retry.assert_called_once_with(error_message)
            mock_handle_failure.assert_not_called()
