#!/usr/bin/env python
# encoding: utf-8

"""
@author: edsion
@file: tasks.py
@time: 2019-02-18 11:30
"""
import os
import time
import uuid
import requests
from datetime import timedelta
from requests.adapters import HTTPAdapter
from celery import shared_task
from celery.utils.log import get_task_logger
from celery_once import QueueOnce, AlreadyQueued
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.core import serializers
from .models import AccessToken

__all__ = ['refresh_access_token', 'get_or_create_user', 'send_message_to_user']
logger = get_task_logger(__name__)

session = requests.session()
session.mount('http://', HTTPAdapter(max_retries=3))
session.mount('https://', HTTPAdapter(max_retries=3))


def get_access_token() -> str:
    """从数据库读取最新的access token，如果过期则刷新（存数据库时已将过期时间适当提前）"""
    start = time.time()
    while time.time() - start < 30:
        try:
            ak = AccessToken.objects.latest('expires_in')
            logger.debug(serializers.serialize('json', [ak]))
            if timezone.now() > ak.expires_in:
                logger.warning(f'access token expired: {ak}')
                try:
                    refresh_access_token.delay(os.getenv('WEWORK_CORP_ID'), os.getenv('WEWORK_AGENT_SECRET'))
                except AlreadyQueued:
                    pass
            else:
                return ak.key
        except ObjectDoesNotExist:
            try:
                refresh_access_token.delay(os.getenv('WEWORK_CORP_ID'), os.getenv('WEWORK_AGENT_SECRET'))
            except AlreadyQueued:
                pass


@shared_task(base=QueueOnce, autoretry_for=(AssertionError,), default_retry_delay=1)
def refresh_access_token(corp_id: str, agent_secret: str) -> str:
    """刷新access token，使用celery_once实现锁（防止触发频率限制）"""
    r = session.get(url='https://qyapi.weixin.qq.com/cgi-bin/gettoken',
                    params={'corpid': corp_id, 'corpsecret': agent_secret},
                    timeout=5)
    logger.debug(r.text)
    res = r.json()
    if res.get('errcode') != 0:
        logger.error(res)
        raise AssertionError
    else:
        ak = res.get('access_token')
        expires_in = timezone.now() + timedelta(seconds=(res.get('expires_in') - 60))
        created = AccessToken.objects.create(key=ak, expires_in=expires_in)
        logger.debug(f'created new access token: {created}')
        return ak


@shared_task(bind=True, autoretry_for=(AssertionError,), default_retry_delay=1)
def get_or_create_user(self, auth_code: str) -> str:
    """根据code获取成员信息。当用户为企业成员时返回username，当用户为非企业成员时返回空字符串
    接口：https://work.weixin.qq.com/api/doc#90000/90135/91023"""
    if self.app.main == 'celery.tests':  # 测试代码，不请求直接返回结果
        res = {'errcode': 0, 'UserId': uuid.uuid4()}
    else:
        r = session.get('https://qyapi.weixin.qq.com/cgi-bin/user/getuserinfo',
                        params={'access_token': get_access_token(), 'code': auth_code})
        logger.debug(r.text)
        res = r.json()
    if res.get('errcode', -1) != 0:
        logger.error(res)
        raise AssertionError
    else:
        user_id = res.get('UserId')
        if res.get("OpenId"):  # TODO: 非企业成员授权时返回"OpenId"，此时无法推送消息?
            return ""
        elif user_id:
            obj, created = User.objects.get_or_create(username=user_id, defaults={'username': user_id})
            return obj.username


@shared_task(bind=True, autoretry_for=(AssertionError,), default_retry_delay=1)
def send_message_to_user(self, users: str, content: str):
    if self.app.main == 'celery.tests':  # 测试代码
        res = {'errcode': 0}
    else:
        r = session.post(url=f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={get_access_token()}',
                         json={'touser': users, "msgtype": "text", 'agentid': os.getenv('WEWORK_AGENT_ID'),
                               'text': {'content': content}}
                         )
        logger.debug(r.text)
        res = r.json()
    if res['errcode'] != 0:
        logger.error(res)
        raise AssertionError
    return res
