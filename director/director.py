import json
import os
import threading
import time
import uuid

import celery.states as states
import pika
import requests
from celery.result import AsyncResult
from flask import Flask, abort, jsonify, request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pipeline_models import Base, ComputationalPipeline, ComputationalTask
from worker import celery

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
    print("Log: {}".format(body))

def _prog_callback(ch, method, properties, body):
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


app = Flask(__name__)

@app.route('/drop_pipeline_db')
def drop_pipeline_db():
    Base.metadata.drop_all(db)
    Base.metadata.create_all(db)
    return "DB tables delete and recreated"

@app.route('/stop_pipeline')
def stop_pipeline():
    return "Pipeline stopped"

@app.route('/start_pipeline', methods=['POST'])
def start_pipeline():
    if not request.json:
        abort(400)
    
    # try to parse data
    data = request.json
    pipeline_name = data['pipeline_name']
    nodes = data['nodes']
    dag_adjacency_list = data['dag']
   
    pipeline = ComputationalPipeline(dag_adjacency_list=dag_adjacency_list,
        state=0)

    session.add(pipeline)
    session.flush()

    pipeline_id = pipeline.pipeline_id

    internal_id = 1
    for node_id in nodes:
        new_task = ComputationalTask(pipeline_id=pipeline_id, node_id=node_id, internal_id=internal_id)
        internal_id = internal_id+1
        session.add(new_task)

    session.commit()

    task = celery.send_task('mytasks.pipeline', args=(pipeline_id,), kwargs={})

    response = {}
    response['pipeline_name'] = pipeline_name
    response['pipeline_id'] = pipeline_id
    
    return jsonify(response)

@app.route("/calc", methods=['GET'])
def calc():
    #ata = request.get_json()
   
    data_str = """{
    "input": 
    [
           {
           	"name": "N", 
               	"value": 10
           }, 
           {
           	"name": "xmin", 
               	"value": -1.0
           }, 
           {
           	"name": "xmax", 
               	"value": 1.0
           },
           {
               	"name": "func", 
               	"value": "exp(x)*sin(x)"
           }
    ],
    "container":
    {
    	"name": "masu.speag.com/comp.services/sidecar-solver",
        "tag": "1.1"
    }
    }"""

    data = json.loads(data_str)
    task = celery.send_task('mytasks.run', args=[data], kwargs={})
         
    return "submitted"

if __name__ == "__main__":
    app.run(port=8010, debug=True, host='0.0.0.0', threaded=True)
