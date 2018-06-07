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
from simcore_sdk.config.db_config import Config as db_config
from simcore_sdk.config.pika_config import Config as pika_config
from simcore_sdk.config.rabbit_config import Config as rabbit_config

 # db config
db_config = db_config()
db = create_engine(db_config.endpoint, client_encoding='utf8')
Session = sessionmaker(db)
session = Session()
Base.metadata.create_all(db)

# pika config
pika_config = pika_config()
pika_log_channel = pika_config.log_channel
pika_progress_channel = pika_config.progress_channel
rabbit_config = rabbit_config()
rabbit_broker = rabbit_config.broker

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
    connection = await aio_pika.connect(rabbit_broker, connection_attempts=100)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    
    logs_exchange = await channel.declare_exchange(
        pika_log_channel, aio_pika.ExchangeType.FANOUT
    )

    progress_exchange = await channel.declare_exchange(
        pika_progress_channel, aio_pika.ExchangeType.FANOUT
    )

    # Declaring queue
    queue = await channel.declare_queue(exclusive=True)

    # Binding the queue to the exchange
    await queue.bind(logs_exchange)
    await queue.bind(progress_exchange)

    # Start listening the queue with name 'task_queue'
    await queue.consume(on_message)