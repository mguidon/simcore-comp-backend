import hashlib
import json
import os
import random
import shutil
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import docker
import pika
from celery import Celery
from celery.result import AsyncResult
from celery.signals import (after_setup_logger, task_failure, task_postrun,
                            task_prerun)
from celery.states import SUCCESS
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pipeline_models import (FAILED, PENDING, RUNNING, SUCCESS, UNKNOWN, Base,
                             ComputationalPipeline, ComputationalTask)

env = os.environ
RABBITMQ_USER = env.get('RABBITMQ_USER','simcore')
RABBITMQ_PASSWORD = env.get('RABBITMQ_PASSWORD','simcore')
RABBITMQ_LOG_CHANNEL = env.get('RABBITMQ_LOG_CHANNEL','comp.backend.channels.log')
RABBITMQ_PROGRESS_CHANNEL = env.get('RABBITMQ_PROGRESS_CHANNEL','comp.backend.channels.progress')
RABBITMQ_HOST="rabbit"
RABBITMQ_PORT=5672

AMQ_URL = 'amqp://{user}:{pw}@{url}:{port}'.format(user=RABBITMQ_USER, pw=RABBITMQ_PASSWORD, url=RABBITMQ_HOST, port=RABBITMQ_PORT)

CELERY_BROKER_URL = AMQ_URL
CELERY_RESULT_BACKEND=env.get('CELERY_RESULT_BACKEND','rpc://')

celery= Celery('tasks',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND)

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials, connection_attempts=100)

io_dirs = {}
pool = ThreadPoolExecutor(1)
run_pool = True

env = os.environ

POSTGRES_URL = "postgres:5432"
POSTGRES_USER = env.get("POSTGRES_USER", "simcore")
POSTGRES_PW = env.get("POSTGRES_PASSWORD", "simcore")
POSTGRES_DB = env.get("POSTGRES_DB", "simcoredb")

DB_URL = 'postgresql+psycopg2://{user}:{pw}@{url}/{db}'.format(user=POSTGRES_USER, pw=POSTGRES_PW, url=POSTGRES_URL, db=POSTGRES_DB)

db = create_engine(DB_URL, client_encoding='utf8')

Session = sessionmaker(db)
session = Session()

def delete_contents(folder):
    for the_file in os.listdir(folder):
        file_path = os.path.join(folder, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path): shutil.rmtree(file_path)
        except Exception as e:
            print(e)

def create_directories(task_id):
    global io_dirs
    for d in ['input', 'output', 'log']:
        dir = os.path.join("/", d, task_id)
        io_dirs[d] = dir
        if not os.path.exists(dir):
            os.makedirs(dir)
        else:
            delete_contents(dir)


def parse_input_data(data):
    global io_dirs 
    for d in data:
        if "type" in d and d["type"] == "url":
            r = requests.get(d["url"])
            filename = os.path.join(io_dirs['input'], d["name"])
            with open(filename, 'wb') as f:
                f.write(r.content)
    filename = os.path.join(io_dirs['input'], 'input.json')
    with open(filename, 'w') as f:
        f.write(json.dumps(data))
                
def fetch_container(data):
    image_name = data['name']
    image_tag = data['tag']
    client = docker.from_env(version='auto')
    client.login(registry="masu.speag.com/v2", username="z43", password="z43")
    client.images.pull(image_name, tag=image_tag)
    docker_image_name = image_name + ":" + image_tag
    return docker_image_name

def prepare_input_and_container(data):
    docker_image_name = ""
    if 'input' in data:
        parse_input_data(data['input'])

    if 'container' in data:
        docker_image_name = fetch_container(data['container'])

    return docker_image_name

def _bg_job(task, task_id, log_file):
    log_key = task_id + ":log"
    prog_key = task_id + ":progress"

    # not sure whether we have to check for existence
#REDIS     if not r.exists(log_key):
#REDIS         r.rpush(log_key, 'This is gonna be the log')
#REDIS     if not r.exists(prog_key):
#REDIS         r.rpush(prog_key, 'This is gonna be the progress')
    
    with open(log_file) as file_:
        # Go to the end of file
        file_.seek(0,2)
        while run_pool:
            curr_position = file_.tell()
            line = file_.readline()
            if not line:
                file_.seek(curr_position)
                time.sleep(1)
            else:
                clean_line = line.strip()
                if clean_line.startswith("[Progress]"):
                    percent = clean_line.lstrip("[Progress]").rstrip("%").strip()
#REDIS                     r.rpush(prog_key, percent.encode('utf-8'))
#REDIS                 else:
#REDIS                     r.rpush(log_key, clean_line.encode('utf-8'))
 
#REDIS     r.set(task_id, "done")
    
def start_container(task, task_id, docker_image_name, stage, io_env):
    global run_pool
    global io_dirs

    run_pool = True
    
    client = docker.from_env(version='auto')
   
    task.update_state(task_id=task_id, state='RUNNING')
    # touch output file
    log_file = os.path.join(io_dirs['log'], "log.dat")

    Path(log_file).touch()
    fut = pool.submit(_bg_job, task, task_id, log_file)

    client.containers.run(docker_image_name, "run", 
         detach=False, remove=True,
         volumes = {'workflow_input'  : {'bind' : '/input'}, 
                    'workflow_output' : {'bind' : '/output'},
                    'workflow_log'    : {'bind'  : '/log'}},
         environment=io_env)

    time.sleep(10)
    run_pool = False
    while not fut.done():
        time.sleep(0.1)

    # hash output
    output_hash = hash_job_output()

    store_job_output(output_hash)

    return output_hash

def hash_job_output():
    output_hash = hashlib.sha256()
    directory = io_dirs['output']

    if not os.path.exists (directory):
        return -1

    try:
        for root, dirs, files in os.walk(directory):
            for names in files:
                filepath = os.path.join(root,names)
                try:
                    f1 = open(filepath, 'rb')
                except:
                    # You can't open the file for some reason
                    f1.close()
                    continue

                while 1:
                    # Read file in as little chunks
                    buf = f1.read(4096)
                    if not buf : break
                    output_hash.update(buf)
                f1.close()
    except:
        import traceback
        # Print the stack traceback
        traceback.print_exc()
        return -2

    return output_hash.hexdigest() 

def store_job_output(output_hash):
    pass
#MONGO    db_client = MongoClient("mongodb://database:27017/")
#MONGO    output_database = db_client.output_database
#MONGO    output_collections = output_database.output_collections
#MONGO    file_db = db_client.file_db
#MONGO    fs = gridfs.GridFS(file_db)
#MONGO    directory = io_dirs['output']
#MONGO    data = {}
#MONGO    if not os.path.exists (directory):
#MONGO        return
#MONGO    try:
#MONGO        output_file_list = []
#MONGO        ids = []
#MONGO        for root, dirs, files in os.walk(directory):
#MONGO            for names in files:
#MONGO                filepath = os.path.join(root,names)
#MONGO                file_id = fs.put(open(filepath,'rb'))
#MONGO                ids.append(file_id)
#MONGO                with open(filepath, 'rb') as f:
#MONGO                    file_data = f.read()
#MONGO                    current = { 'filename' : names, 'contents' : file_data }
#MONGO                    output_file_list.append(current)
#MONGO
#MONGO        data["output"] = output_file_list
#MONGO        data["_hash"] = output_hash
#MONGO        data["ids"] = ids
#MONGO
#MONGO        output_collections.insert_one(data)
#MONGO
#MONGO    except:
#MONGO        import traceback
#MONGO        # Print the stack traceback
#MONGO        traceback.print_exc()
#MONGO        return -2

def do_run(task, task_id, data):
    docker_image_name = prepare_input_and_container(data)
    io_env = []
    io_env.append("INPUT_FOLDER=/input/"+task_id)
    io_env.append("OUTPUT_FOLDER=/output/"+task_id)
    io_env.append("LOG_FOLDER=/log/"+task_id)
 
  
    return start_container(task, task_id, docker_image_name, "run", io_env)

@celery.task(name='mytasks.run', bind=True)
def run(self, data):
    task = self
    task_id = task.request.id

    create_directories(task_id)
    
    return str(do_run(task, task_id, data))

def find_entry_point(G):
    result = []
    for node in G.nodes:
        if len(list(G.predecessors(node))) == 0:
            result.append(node)
    return result

#@task_prerun.connect
#def prerun(*args, **kwargs):
#    global session
#    session = Session()
#
#
#@task_postrun.connect
#def postrun(*args, **kwargs):
#    session.flush()
#    session.close()

def _is_node_ready(task, graph):
    tasks = session.query(ComputationalTask).filter(ComputationalTask.node_id.in_(list(graph.predecessors(task.node_id)))).all()

    print("TASK {} ready? Checking ..".format(task.node_id))
    for dep_task in tasks:
        job_id = dep_task.job_id
        if job_id:
            print("DEPENDS ON {} with job_id {} and stat {}".format(dep_task.node_id, job_id, dep_task.state))
        if not dep_task.job_id or \
            not dep_task.state == SUCCESS:
            return False
    return True

def _process_task_node(celery_task, task, task_id, pipeline_id, node_id):
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.exchange_declare(exchange=RABBITMQ_LOG_CHANNEL, exchange_type='fanout')
    channel.exchange_declare(exchange=RABBITMQ_PROGRESS_CHANNEL, exchange_type='fanout')

    task.job_id = task_id
    task.state = RUNNING
    session.commit()
    print('Runnning Pipeline {} and node {}'.format(pipeline_id, task.internal_id))

    task_sleep = random.randint(2,8)
    dp = 1.0 / (task_sleep-1)
    for i in range(task_sleep):
        msg = "{}: Sleep, sec: {}".format(task.internal_id, i)
        prog_msg = "{} %".format(i*dp * 100)
        channel.basic_publish(exchange=RABBITMQ_PROGRESS_CHANNEL, routing_key='', body=prog_msg)
        channel.basic_publish(exchange=RABBITMQ_LOG_CHANNEL, routing_key='', body=msg)
        time.sleep(1)

    # postprocess
    task.state = SUCCESS
    session.commit()
    connection.close()
    
@celery.task(name='mytasks.pipeline', bind=True)
def pipeline(self, pipeline_id, node_id=None):
    pipeline = session.query(ComputationalPipeline).filter_by(pipeline_id=pipeline_id).one()
    graph = pipeline.execution_graph
    next_task_nodes = []
    if node_id:
        task = session.query(ComputationalTask).filter_by(node_id=node_id).one()

        # already done or running and happy
        if task.job_id and task.state == SUCCESS or task.state == RUNNING:
            print("ALREADY DONE", task.job_id, task.internal_id)
            return
        # not yet ready
        if not _is_node_ready(task, graph):
            print("NODE {} NOT YET READY".format(task.internal_id))
            return

        _process_task_node(self, task, self.request.id, pipeline_id, node_id)

        next_task_nodes = list(graph.successors(node_id))
    else:
        next_task_nodes = find_entry_point(graph)

    self.update_state(state=SUCCESS)

    for node_id in next_task_nodes:
        task = celery.send_task('mytasks.pipeline', args=(pipeline_id, node_id), kwargs={})
