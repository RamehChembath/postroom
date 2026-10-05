import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "postroom.settings")

app = Celery("postroom")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "send-due-post-reminders-daily": {
        "task": "notifications.tasks.send_due_post_reminders",
        "schedule": crontab(hour=7, minute=0),  # 7am server time (TIME_ZONE setting)
    },
}
