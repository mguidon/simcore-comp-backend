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

FROM python:3

RUN pip install aiohttp aiohttp-swagger aiohttp-devtools python-socketio requests \
    networkx sqlalchemy psycopg2 celery sqlalchemy-json pika

EXPOSE 8011

WORKDIR /work/director

ENTRYPOINT ["python", "server.py"] 
