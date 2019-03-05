FROM python:3.6-alpine as django
COPY . /app/
WORKDIR /app
ENV TZ="Asia/Shanghai"
RUN set -o pipefail \
    && apk add --no-cache tzdata \
    && pip config --global set global.index-url https://mirrors.aliyun.com/pypi/simple/ \
    && pip config --global set global.trusted-host mirrors.aliyun.com \
    && pip config --global set global.no-cache-dir true \
    && pip config --global list \
    && pip install --upgrade pip pipenv \
    && pipenv install --system --deploy --clear
CMD ["/usr/local/bin/gunicorn","--config","python:gunicorn_conf","pytest_backend.wsgi"]

FROM python:3.6-alpine as celery
WORKDIR /app
ENV TZ="Asia/Shanghai"
COPY --from=django /app .
COPY --from=django /usr/local/lib/python3.6 /usr/local/lib/python3.6
COPY --from=django /usr/local/bin/ /usr/local/bin/
COPY --from=django /usr/share/zoneinfo/ /usr/share/zoneinfo/
CMD ["/usr/local/bin/celery","worker","--app" ,"pytest_backend","--beat","--logfile=/var/log/celery.log","--loglevel=INFO"]
