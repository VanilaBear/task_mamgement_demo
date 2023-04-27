import logging
import time
import traceback
from abc import ABC

from celery import shared_task, Task

from core.constants import STATUS_COMPLETED, STATUS_FAILED, STATUS_RETRY_PENDING
from core.exceptions import TaskException, UnknownTaskException
from core.models import TaskMeta

logger = logging.getLogger(__name__)


class BaseSampleTask(Task, ABC):
    """Base class for task processing"""

    countdown: int = 60
    max_retries: int = 0

    def _get_task_meta(self) -> TaskMeta:
        """Returns associated TaskMeta instance"""

        return TaskMeta.objects.get(id=self.task_id)

    def _init_config(self, **kwargs):
        """
        Inits task configuration

        :param kwargs: named parameters for task configuration
        :return:
        """

        self.task_id = self.request.id
        for attr in ["countdown", "max_retries"]:
            if value := kwargs.get(attr):
                setattr(self, attr, value)

    def _log_attempt_number(self):
        """Creates a log about attempt number"""

        attempt_message = f"Attempt {self.request.retries + 1} of {self.max_retries + 1}..."
        logger.warning(attempt_message) if self.request.retries else logger.info(attempt_message)

    def _perform_task(self, param1: int, param2: str):
        """
        Makes some actions with task

        :param param1: sleeping time in seconds
        :param param2: string parameter
        """

        task = self._get_task_meta()

        task.start()

        if param2 == "raise exception before":
            raise Exception("Manual exception before execution.")

        time.sleep(param1)

        if param2 == "raise exception after":
            raise Exception("Manual exception after execution.")

        task.finish(STATUS_COMPLETED)
        logger.info(f"The task {self.task_id} has been successfully completed.")

    def _handle_retry(self, error: str):
        """
        Handles retrying logic

        :param error: error message string
        """

        logger.warning(f"Sending for retry ...")
        task = self._get_task_meta()
        task.add_error(error, traceback.format_exc())
        task.finish(STATUS_RETRY_PENDING)
        raise self.retry(exc=UnknownTaskException(f"{error}"), max_retries=self.max_retries, countdown=self.countdown)

    def _handle_failure(self):
        """Handles failure logic"""

        task = self._get_task_meta()
        task.finish(STATUS_FAILED)
        logger.error(f"Failed to complete the task {self.task_id}.")


@shared_task(bind=True, base=BaseSampleTask)
def sample_task(self, param1: int, param2: str, **kwargs):
    """
    Processes task

    :param self: task instance (provided by Celery)
    :param param1: sleeping time in seconds
    :param param2: string parameter
    :param kwargs: named parameters for task configuration
    """

    self._init_config(**kwargs)
    logger.info(f"Starting task execution [id: {self.task_id}; param1: {param1}, param2: {param2}] ...")
    self._log_attempt_number()
    try:
        self._perform_task(param1, param2)
    except TaskMeta.DoesNotExist:
        logger.warning(f"Task {self.task_id} not found")
    except TaskException as known_error:
        logger.warning(str(known_error))
    except Exception as error:
        if self.request.retries < self.max_retries:
            self._handle_retry(str(error))
        else:
            self._handle_failure()
