#!/usr/bin/env python
# encoding: utf-8

"""
@author: edsion
@file: conftest.py
@time: 2019-03-03 22:00
"""

from celery import Celery
import pytest
from _pytest.fixtures import SubRequest
from pytest_backend.celery import app
from celery.contrib.pytest import _create_app


@pytest.fixture(scope='session')
def celery_parameters() -> dict:
    """celery测试配置"""
    return {
        'broker_url': 'redis://redis:6379/1',
        'result_backend': 'redis://redis:6379/1',
        'ONCE': {
            'backend': 'celery_once.backends.Redis',
            'settings': {
                'url': app.conf.broker_url,
                'default_timeout': 60
            }
        }
    }


@pytest.fixture(scope='session')
def celery_session_app(request: SubRequest,
                       celery_config: dict,
                       celery_parameters: dict,
                       celery_enable_logging: bool,
                       use_celery_app_trap: bool,
                       ) -> Celery:
    """将get_marker替换为get_closest_marker（pytest的兼容问题）"""
    mark = request.node.get_closest_marker('celery')
    config = dict(celery_config, **mark.kwargs if mark else {})
    with _create_app(enable_logging=celery_enable_logging,
                     use_trap=use_celery_app_trap,
                     parameters=celery_parameters,
                     **config) as app:
        if not use_celery_app_trap:
            app.set_default()
            app.set_current()
        yield app
