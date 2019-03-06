import os
import random
import string
import logging
from django.shortcuts import render
from django.utils.http import urlquote
from django.http.response import HttpResponseRedirect
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from .tasks import get_or_create_user, send_message_to_user

logger = logging.getLogger(__name__)


def random_str():
    """生成随机字符串
    企业微信的state字段，限制是128个字节"""
    return ''.join(random.sample(string.ascii_letters + string.digits, random.randint(8, 32)))


@api_view(['GET', ])
@permission_classes([AllowAny])
def qr_connect(request: Request) -> Response or HttpResponseRedirect:
    """扫码授权登录"""
    auth_code = request.query_params.get('code')
    if auth_code:
        if not request.query_params.get('state'):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        # TODO:与网页授权不同，肯定能拿到用户？（未认证企业，微信扫码强制跳转企业微信）
        username = get_or_create_user.delay(auth_code).get()
        if request.query_params.get('cancel'):  # 因为要验证身份才能取消授权，所以不在redirect前执行
            try:
                Token.objects.get(user__username=username).delete()
            except ObjectDoesNotExist:
                logger.warning('token not exist.')
            send_message_to_user.delay(username, "授权已清除")
            return render(request, 'oauth_page.html', context={'title': "授权已清除", "reason": "请查看应用消息"})
        else:
            this_user = User.objects.get(username=username)
            obj, created = Token.objects.get_or_create(user=this_user, defaults={'user': this_user})
            send_message_to_user.delay(username, obj.key)
            return render(request, 'oauth_page.html', context={'title': "授权成功", "reason": "请查看应用消息"})

    else:
        logger.debug(f'redirect_uri:{request.build_absolute_uri()}')
        return HttpResponseRedirect(
            redirect_to=f'https://open.work.weixin.qq.com/wwopen/sso/qrConnect?'
            f'appid={os.getenv("WEWORK_CORP_ID")}'
            f'&agentid={os.getenv("WEWORK_AGENT_ID")}'
            f'&redirect_uri={urlquote(request.build_absolute_uri())}'
            f'&state={random_str()}')


@api_view(['GET', ])
@permission_classes([AllowAny])
def oauth2(request: Request) -> Response or HttpResponseRedirect:
    """网页授权登录（只能在微信和企业微信客户端访问）"""
    # TODO:认证企业，如果获取到的user是OpenID（微信中打开链接），是否可以换取UserID，或者推送消息？
    auth_code = request.query_params.get('code')
    if auth_code:
        if not request.query_params.get('state'):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        username = get_or_create_user.delay(auth_code).get()
        if not username:
            return render(request, 'oauth_page.html',
                          context={'title': '授权失败', 'reason': "无法获取用户信息"})
        if request.query_params.get('cancel'):
            try:
                Token.objects.get(user__username=username).delete()
            except Token.DoesNotExist:
                logger.warning('token not exist.')
            send_message_to_user.delay(username, "授权已清除")
            return render(request, 'oauth_page.html', context={'title': "授权已清除"})
        else:
            this_user = User.objects.get(username=username)
            obj, created = Token.objects.get_or_create(user=this_user, defaults={'user': this_user})
            send_message_to_user.delay(username, obj.key)
            return render(request, 'oauth_page.html', context={'title': "授权成功", "auto_close": True})
    else:
        logger.debug(f'redirect_uri:{request.build_absolute_uri()}')
        return HttpResponseRedirect(
            redirect_to=f'https://open.weixin.qq.com/connect/oauth2/authorize?'
            f'appid={os.getenv("WEWORK_CORP_ID")}'
            f'&redirect_uri={urlquote(request.build_absolute_uri())}'
            f'&response_type=code&scope=snsapi_base'
            f'&state={random_str()}'
            f'#wechat_redirect')


@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication, ])
@permission_classes([IsAuthenticated, ])
def notify_myself(request: Request) -> Response:
    """给自己发送应用消息"""
    query = request.query_params.get('content')
    body = request.data.get('content')
    if query:
        content = query
    elif body:
        content = body
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    res = send_message_to_user.delay(request.user.username, content)
    return Response(data={'id': res.id}, status=status.HTTP_201_CREATED)
