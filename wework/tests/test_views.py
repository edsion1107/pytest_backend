#!/usr/bin/env python
# encoding: utf-8

"""
@author: edsion
@file: test_views.py
@time: 2019-03-03 15:46
"""
import uuid
import pytest
import allure
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from wework.views import random_str


@allure.feature("授权")
@pytest.mark.parametrize("path", ['/wework/oauth2', '/wework/qr_connect'])
def test_oauth2_redirect(path):
    """直接访问（不带参数时）302跳转"""
    res = APIClient().get('/wework/oauth2')
    assert res.status_code == 302
    assert 'https://open.weixin.qq.com' in res.url


@allure.feature("授权")
@pytest.mark.parametrize("path", ['/wework/oauth2', '/wework/qr_connect'])
def test_oauth2_block(celery_session_app, celery_session_worker, path):
    """模拟非法请求（不带state参数）的情况"""
    with pytest.raises(AssertionError):
        APIClient().get(path, data={'code': uuid.uuid4()})


@pytest.mark.django_db
@allure.feature("授权")
@pytest.mark.parametrize("path", ['/wework/oauth2', '/wework/qr_connect'])
def test_oauth2_success(celery_session_app, celery_session_worker, path):
    """带参数模拟成功授权的情况"""
    res = APIClient().get(path, data={'code': uuid.uuid4(), 'state': random_str()})
    assert res.status_code == 200
    assert res.context['title'] == "授权成功"
    assert 'oauth_page.html' in [i.name for i in res.templates]


@pytest.mark.django_db
@allure.feature("授权")
@pytest.mark.parametrize("path", ['/wework/oauth2', '/wework/qr_connect'])
def test_oauth2_cancel(celery_session_app, celery_session_worker, path):
    """带参数模拟取消授权的情况"""
    res = APIClient().get(path, data={'code': uuid.uuid4(), 'state': random_str(), 'cancel': True})
    assert res.status_code == 200
    assert res.context['title'] == "授权已清除"
    assert 'oauth_page.html' in [i.name for i in res.templates]


@allure.feature("授权")
@pytest.mark.parametrize("path", ['/wework/oauth2', '/wework/qr_connect'])
def test_oauth2_http_method(path):
    """测试各种http方法的支持情况"""
    assert APIClient().get(path).status_code == 302
    assert APIClient().options('/wework/oauth2').status_code == 200

    assert APIClient().post(path).status_code == 405
    assert APIClient().head(path).status_code == 405
    assert APIClient().put(path).status_code == 405
    assert APIClient().patch(path).status_code == 405


@allure.feature("通知")
def test_notify_myself_unauthorized():
    """身份验证未通过"""
    assert APIClient().get('/wework/notification').status_code == 401
    assert APIClient().get('/wework/notification', data={'content': random_str()}).status_code == 401


@pytest.mark.django_db
@allure.feature("通知")
def test_notify_myself_method_get(celery_session_app):
    """支持GET请求"""
    user = User.objects.create(username=uuid.uuid4(), is_active=False, is_staff=False, is_superuser=False)
    token = Token.objects.create(user=user)
    client = APIClient()
    client.force_authenticate(user, token)
    r = client.get('/wework/notification', data={'content': random_str()})
    assert r.status_code == 201
    assert r.data.get('id')


@pytest.mark.django_db
@allure.feature("通知")
def test_notify_myself_method_post(celery_session_app):
    """支持POST请求"""
    user = User.objects.create(username=uuid.uuid4(), is_active=False, is_staff=False, is_superuser=False)
    token = Token.objects.create(user=user)
    client = APIClient()
    client.force_authenticate(user, token)

    # 默认content_type为'multipart/form-data'
    r = client.post('/wework/notification', data={'content': random_str()})
    assert r.status_code == 201
    assert r.data.get('id')

    # content_type为'application/json'的情况
    r = client.post('/wework/notification', data={'content': random_str()}, format='json')
    assert r.status_code == 201
    assert r.data.get('id')


@pytest.mark.django_db
@allure.feature("通知")
def test_notify_myself_bad_request(celery_session_app, celery_session_worker):
    """支持GET请求"""
    user = User.objects.create(username=uuid.uuid4(), is_active=False, is_staff=False, is_superuser=False)
    token = Token.objects.create(user=user)
    client = APIClient()
    client.force_authenticate(user, token)
    r = client.get('/wework/notification')
    assert r.status_code == 400
    assert not r.data
