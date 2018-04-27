import json
import os
import threading
import time
import uuid

import celery.states as states
import pika
import requests
from celery.result import AsyncResult
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pipeline_models import Base, ComputationalPipeline, ComputationalTask
from worker import celery

from async_sio import sio

env = os.environ

POSTGRES_URL = "postgres:5432"
POSTGRES_USER = env.get("POSTGRES_USER", "simcore")
POSTGRES_PW = env.get("POSTGRES_PASSWORD", "simcore")
POSTGRES_DB = env.get("POSTGRES_DB", "simcoredb")

DB_URL = 'postgresql+psycopg2://{user}:{pw}@{url}/{db}'.format(user=POSTGRES_USER, pw=POSTGRES_PW, url=POSTGRES_URL, db=POSTGRES_DB)

db = create_engine(DB_URL, client_encoding='utf8')

Session = sessionmaker(db)
session = Session()

Base.metadata.create_all(db)

RABBITMQ_USER = env.get('RABBITMQ_USER','simcore')
RABBITMQ_PASSWORD = env.get('RABBITMQ_PASSWORD','simcore')
RABBITMQ_LOG_CHANNEL = env.get('RABBITMQ_LOG_CHANNEL','comp.backend.channels.log')
RABBITMQ_PROGRESS_CHANNEL = env.get('RABBITMQ_PROGRESS_CHANNEL','comp.backend.channels.progress')
RABBITMQ_HOST="rabbit"
RABBITMQ_PORT=5672

AMQ_URL = 'amqp://{user}:{pw}@{url}:{port}'.format(user=RABBITMQ_USER, pw=RABBITMQ_PASSWORD, url=RABBITMQ_HOST, port=RABBITMQ_PORT)

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials, connection_attempts=100)
connection = pika.BlockingConnection(parameters)
channel = connection.channel()

def _log_callback(ch, method, properties, body):
    log = "{}".format(body)
    sio.emit("logger", data = log)
    print("Log: {}".format(body))

def _prog_callback(ch, method, properties, body):
    progress = "{}".format(body)
    sio.emit("progress", data = progress)
    print("Progress: {}".format(body))

callbacks = {RABBITMQ_LOG_CHANNEL : _log_callback, RABBITMQ_PROGRESS_CHANNEL : _prog_callback}


for ch in [RABBITMQ_PROGRESS_CHANNEL]:
    channel.queue_declare(queue=ch)
    channel.exchange_declare(exchange=ch, exchange_type='fanout')

    result = channel.queue_declare(exclusive=True)
    queue_name = result.method.queue

    channel.queue_bind(exchange=ch, queue=queue_name)

    def _consume_logs(channel, callback, queue):
        print("CONSUMER THREAD STARTED")
        channel.basic_consume(callback, queue=queue, no_ack=True)

        t1 = threading.Thread(target=channel.start_consuming)
        t1.start()
        t1.join(0)

    _consume_logs(channel, callbacks[ch], queue_name)

for ch in [RABBITMQ_LOG_CHANNEL]:
    channel.queue_declare(queue=ch)
    channel.exchange_declare(exchange=ch, exchange_type='fanout')

    result = channel.queue_declare(exclusive=True)
    queue_name = result.method.queue

    channel.queue_bind(exchange=ch, queue=queue_name)

    def _consume_logs(channel, callback, queue):
        print("CONSUMER THREAD STARTED")
        channel.basic_consume(callback, queue=queue, no_ack=True)

        t1 = threading.Thread(target=channel.start_consuming)
        t1.start()
        t1.join(0)

    _consume_logs(channel, callbacks[ch], queue_name)