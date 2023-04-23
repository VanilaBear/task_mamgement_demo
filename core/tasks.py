import logging
import time
import uuid

from celery import shared_task
from django.utils.timezone import now

from core.constants import STATUS_COMPLETED, STATUS_FAILED, STATUS_RETRY_PENDING
from core.exceptions import TaskException, UnknownTaskException
from core.models import TaskMeta

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def sample_task(self, task_id: uuid, param1: int, param2: str, countdown: int = 60, max_retries: int = 0):
    logger.info(f"Starting task execution [id: {task_id}; param1: {param1}, param2: {param2}] ...")
    try:
        task = TaskMeta.objects.get(id=task_id)
        task.start()

        if param2 == "raise exception before":
            raise Exception("Manual exception before execution.")

        time.sleep(param1)

        if param2 == "raise exception after":
            raise Exception("Manual exception after execution.")

        task.finish(STATUS_COMPLETED)
        logger.error(f"The task {task_id} has been successfully completed.")

    except TaskMeta.DoesNotExist:
        logger.warning(f"Task {task_id} not found")
    except TaskException as known_error:
        logger.warning(str(known_error))
    except Exception as error:
        if self.request.retries < max_retries:
            logger.warning(f"Retrying {self.request.retries + 1} of {max_retries}...")
            TaskMeta.objects.filter(id=task_id).update(status=STATUS_RETRY_PENDING, finished_at=now())
            raise self.retry(exc=UnknownTaskException(f"{str(error)}"), max_retries=max_retries, countdown=countdown)
        TaskMeta.objects.filter(id=task_id).update(status=STATUS_FAILED, finished_at=now())
        logger.error(f"Failed to complete the task {task_id}.")
