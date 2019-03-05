#!/usr/bin/env python
# encoding: utf-8

"""
@author: edsion
@file: urls.py
@time: 2019-02-25 10:40
"""
from django.urls import path
from . import views

urlpatterns = [
    path('oauth2', views.oauth2),
    path('qr_connect', views.qr_connect),
    path('notification', views.notify_myself),
]
