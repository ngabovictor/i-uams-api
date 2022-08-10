from celeryconfig import app
from django_celery_beat.models import PeriodicTask, ClockedSchedule
from users.models import Verification
from datetime import datetime, timedelta

from users.utils import get_object_or_none


@app.task
def schedule_expiration(verification_code):
    """

    :param str verification_code: code identifying verification instance
    :return: None
    """
    kwargs = "{" + "\"id\":" + "\"{}\"".format(verification_code) + "}"

    get_kwargs = {
        "id": verification_code
    }

    verification = get_object_or_none(Verification, get_kwargs)

    if verification:
        created_at = verification.created_at
        expiration_time_delta = timedelta(minutes=5)
        expiration_time = created_at + expiration_time_delta

        schedule = ClockedSchedule.objects.create(
            clocked_time=expiration_time,
        )

        PeriodicTask.objects.create(
            name="auto_invalidate_verification_{code}".format(code=verification_code),
            task="users.tasks.tasks_verification.invalidate_verification",
            kwargs=kwargs,
            clocked=schedule,
            one_off=True
        )


@app.task
def invalidate_verification(*args, **kwargs):
    code = kwargs.get('id')
    verification = Verification.objects.filter(id=code).first()

    if verification:
        verification.is_valid = False
        verification.save()
