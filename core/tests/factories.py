import factory
from django.utils import timezone
from django.utils.timezone import now

from authentication.tests.factories import UserFactory
from core.constants import STATUS_PENDING
from core.models import TaskError, TaskMeta


class TaskMetaFactory(factory.django.DjangoModelFactory):
    """TaskMeta model factory"""

    name = factory.Sequence(lambda n: f"task-{n}")
    status = STATUS_PENDING
    user = factory.SubFactory(UserFactory)
    created_at = timezone.now()
    finished_at = None

    class Meta:
        model = TaskMeta


class TaskErrorFactory(factory.django.DjangoModelFactory):
    """TaskError model factory"""

    task = factory.SubFactory(TaskMetaFactory)
    message = factory.Faker("text")
    traceback = factory.Faker("text")
    created_at = now()

    class Meta:
        model = TaskError
