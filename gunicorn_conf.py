#!/usr/bin/env python
# encoding: utf-8

"""
@author: edsion
@file: gunicorn_conf.py
@time: 2019-02-25 14:40
"""
import multiprocessing

accesslog = '/var/log/gunicorn-access.log'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
errorlog = '/var/log/gunicorn-errors.log'
capture_output = False
loglevel = 'info'

bind = [':8000']
workers = multiprocessing.cpu_count() * 2 + 1
max_requests = 1000
