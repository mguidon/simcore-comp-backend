# FROM node:8.9.2
# 
# LABEL maintainer=pcrespov
# 
# ENV NPM_CONFIG_LOGLEVEL warn
# 
# WORKDIR /home/node/
# 
# RUN npm install qxcompiler
# ENV PATH="/home/node/node_modules/.bin/:${PATH}"
# 
# WORKDIR /home/node/qxapp
# COPY client-qx/source source
# COPY client-qx/*.json ./
# RUN qx compile
# 
# 
# #------------------------------------------------------------------------
FROM python:3.6-alpine

# Selects appropriate 'server-py-*/' folder
ARG serverdir

ENV SIMCORE_WEB_OUTDIR=/usr/src/app/client
ENV SIMCORE_WEB_HOSTNAME='0.0.0.0'
ENV SIMCORE_WEB_PORT=8080

WORKDIR /usr/src/app

VOLUME ${SIMCORE_WEB_OUTDIR}
VOLUME /usr/src/app

RUN apk add --no-cache postgresql-dev gcc libc-dev

RUN pip install aiohttp aiohttp-swagger aiohttp-devtools python-socketio requests \
    networkx sqlalchemy psycopg2 celery sqlalchemy-json aio-pika \
    && pip list --format=columns

EXPOSE $SIMCORE_WEB_PORT

#ENTRYPOINT ["/bin/sh", "-c", "adev runserver --host ${SIMCORE_WEB_HOSTNAME} --port ${SIMCORE_WEB_PORT} --app-factory create_app server.py"]
CMD ["python", "-u", "server.py"]
