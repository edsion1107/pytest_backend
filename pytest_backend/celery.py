#!/usr/bin/env python
# encoding: utf-8

"""
@author: edsion
@file: celery.py
@time: 2019-02-25 10:37
"""

import os
import sentry_sdk
from celery import Celery
from datetime import timedelta

sentry_sdk.init(dsn=os.getenv('SENTRY_DSN'), )

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pytest_backend.settings')

app = Celery('pytest_backend')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
app.conf.broker_url = 'redis://redis:6379/0'
app.conf.result_backend = 'django-db'
app.conf.result_expires = timedelta(days=7)
app.conf.worker_max_tasks_per_child = 10000
app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'

app.conf.ONCE = {
    'backend': 'celery_once.backends.Redis',
    'settings': {
        'url': app.conf.broker_url,
        'default_timeout': 60
    }
}


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
