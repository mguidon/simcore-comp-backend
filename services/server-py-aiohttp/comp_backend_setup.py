import json
import os
import threading
import time
import uuid

import celery.states as states
import pika
import asyncio
import aio_pika

import requests
from celery.result import AsyncResult
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.pipeline_models import Base, ComputationalPipeline, ComputationalTask
from comp_backend_worker import celery

from async_sio import sio
from config.db_config import Config as db_config


 # db config
db_config = db_config()
db = create_engine(db_config.endpoint, client_encoding='utf8')
Session = sessionmaker(db)
session = Session()
Base.metadata.create_all(db)

# rabbit config


RABBITMQ_USER = env.get('RABBITMQ_USER','simcore')
RABBITMQ_PASSWORD = env.get('RABBITMQ_PASSWORD','simcore')
RABBITMQ_LOG_CHANNEL = env.get('RABBITMQ_LOG_CHANNEL','comp.backend.channels.log')
RABBITMQ_PROGRESS_CHANNEL = env.get('RABBITMQ_PROGRESS_CHANNEL','comp.backend.channels.progress')
RABBITMQ_HOST="rabbit"
RABBITMQ_PORT=5672

AMQ_URL = 'amqp://{user}:{pw}@{url}:{port}'.format(user=RABBITMQ_USER, pw=RABBITMQ_PASSWORD, url=RABBITMQ_HOST, port=RABBITMQ_PORT)

async def on_message(message: aio_pika.IncomingMessage):
    with message.process():
        data = json.loads(message.body)
        #print("[x] %r" % data)
        if data["Channel"] == "Log":
            await sio.emit("logger", data = json.dumps(data))
        elif data["Channel"] == "Progress":
            #print(data["Progress"])
            await sio.emit("progress", data = json.dumps(data))

async def subscribe():
    connection = await aio_pika.connect(AMQ_URL,connection_attempts=100)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    
    logs_exchange = await channel.declare_exchange(
        RABBITMQ_LOG_CHANNEL, aio_pika.ExchangeType.FANOUT
    )

    progress_exchange = await channel.declare_exchange(
        RABBITMQ_PROGRESS_CHANNEL, aio_pika.ExchangeType.FANOUT
    )

    # Declaring queue
    queue = await channel.declare_queue(exclusive=True)

    # Binding the queue to the exchange
    await queue.bind(logs_exchange)
    await queue.bind(progress_exchange)

    # Start listening the queue with name 'task_queue'
    await queue.consume(on_message)