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
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker

from pipeline_models import (FAILED, PENDING, RUNNING, SUCCESS, UNKNOWN, Base,
                             ComputationalPipeline, ComputationalTask)

from s3_client import S3Client

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


S3_ENDPOINT = env.get("S3_ENDPOINT", "")
S3_ACCESS_KEY = env.get("S3_ACCESS_KEY", "")
S3_SECRET_KEY = env.get("S3_SECRET_KEY", "")
S3_BUCKET_NAME = env.get("S3_BUCKET_NAME", "")

s3_client = S3Client(endpoint=S3_ENDPOINT, access_key=S3_ACCESS_KEY, secret_key=S3_SECRET_KEY)
s3_client.create_bucket(S3_BUCKET_NAME)

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

def _bg_job(task, log_file):
    connection = pika.BlockingConnection(parameters)

    channel = connection.channel()
    channel.exchange_declare(exchange=RABBITMQ_LOG_CHANNEL, exchange_type='fanout')
    channel.exchange_declare(exchange=RABBITMQ_PROGRESS_CHANNEL, exchange_type='fanout')

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
                if clean_line.lower().startswith("[progress]"):
                    progress = clean_line.lower().lstrip("[progress]").rstrip("%").strip()
                    prog_data = {"Channel" : "Progress", "Node": task.internal_id, "Progress" : progress}
                    prog_body = json.dumps(prog_data)
                    channel.basic_publish(exchange=RABBITMQ_PROGRESS_CHANNEL, routing_key='', body=prog_body)
                else:
                    log_data = {"Channel" : "Log", "Node": task.internal_id, "Message" : clean_line}
                    log_body = json.dumps(log_data)
                    channel.basic_publish(exchange=RABBITMQ_LOG_CHANNEL, routing_key='', body=log_body)

        
    connection.close()
    
def start_container(task, task_id, docker_image_name, io_env):
    global run_pool
    global io_dirs

    run_pool = True
    
    client = docker.from_env(version='auto')

    # touch output file
    log_file = os.path.join(io_dirs['log'], "log.dat")

    Path(log_file).touch()
    fut = pool.submit(_bg_job, task, log_file)

    try:
        client.containers.run(docker_image_name, "run", 
             detach=False, remove=True,
             volumes = {'simcorecompbackend_input'  : {'bind' : '/input'}, 
                        'simcorecompbackend_output' : {'bind' : '/output'},
                        'simcorecompbackend_log'    : {'bind'  : '/log'}},
             environment=io_env)
    except Exception as e:
        print(e)

    time.sleep(1)
    run_pool = False
    while not fut.done():
        time.sleep(0.1)

    # hash output
    #output_hash = hash_job_output()

    process_task_output(task)

    task.state = SUCCESS
    session.add(task)
    session.commit()

    return# output_hash

def process_task_output(task):
    directory = io_dirs['output']
    if not os.path.exists(directory):
        return
    try:
        for root, dirs, files in os.walk(directory):
            for name in files:
                filepath = os.path.join(root, name)
                object_name = str(task.pipeline_id) + "/" + task.job_id + "/" + name
                print("AAAAAAAAAAAAA upload {} as {}".format(filepath, object_name))
                s3_client.upload_file(S3_BUCKET_NAME, object_name, filepath)
        
    except:
        import traceback
        traceback.print_exc()
        return -2

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

def find_entry_point(G):
    result = []
    for node in G.nodes:
        if len(list(G.predecessors(node))) == 0:
            result.append(node)
    return result

def _is_node_ready(task, graph):
    tasks = session.query(ComputationalTask).filter(ComputationalTask.node_id.in_(list(graph.predecessors(task.node_id)))).all()

    print("TASK {} ready? Checking ..".format(task.internal_id))
    for dep_task in tasks:
        job_id = dep_task.job_id
        if not job_id:
            return False
        else:
            print("TASK {} DEPENDS ON {} with stat {}".format(task.internal_id, dep_task.internal_id,dep_task.state))
            if not dep_task.state == SUCCESS:
                return False
    print("TASK {} is ready".format(task.internal_id))
    
    return True
    
def _process_task_node(task, celery_task_id, pipeline_id, node_id):
    # create directories
    create_directories(celery_task_id)

    # fetch container
    image_name = task.service['image_name']
    image_tag = task.service['image_tag']
    client = docker.from_env(version='auto')
    client.login(registry="masu.speag.com/v2", username="z43", password="z43")
    client.images.pull(image_name, tag=image_tag)
    docker_image_name = image_name + ":" + image_tag


    io_env = []
    io_env.append("INPUT_FOLDER=/input/"+celery_task_id)
    io_env.append("OUTPUT_FOLDER=/output/"+celery_task_id)
    io_env.append("LOG_FOLDER=/log/"+celery_task_id)

    print('Runnning Pipeline {} and node {} from container'.format(pipeline_id, task.internal_id))

    start_container(task, celery_task_id, docker_image_name, io_env)

    # postprocess
    task.state = SUCCESS
    session.add(task)
    session.commit()

@celery.task(name='mytasks.pipeline', bind=True)
def pipeline(self, pipeline_id, node_id=None):
    pipeline = session.query(ComputationalPipeline).filter_by(pipeline_id=pipeline_id).one()
    graph = pipeline.execution_graph
    next_task_nodes = []
    if node_id:
        do_process = True

        # find the for the current node_id, skip if there is already a job_id around
        query = session.query(ComputationalTask).filter(and_(ComputationalTask.node_id==node_id, ComputationalTask.job_id==None))
        # Use SELECT FOR UPDATE TO lock the row
        query.with_for_update()
        try:
            task = query.one()
        except:
            # no result found, just return
            return
        if task == None:
            return
   
        # already done or running and happy
        if task.job_id and (task.state == SUCCESS or task.state == RUNNING):
            print("TASK {} ALREADY DONE OR RUNNING".format(task.internal_id))
            do_process = False

        # Check if node's dependecies are there
        if not _is_node_ready(task, graph):
            print("TASK {} NOT YET READY".format(task.internal_id))
            do_process = False

        if do_process:           
            task.job_id = self.request.id
            session.add(task)
            session.commit()
        else:
            return

        task = session.query(ComputationalTask).filter_by(node_id=node_id).one()
        if task.job_id != self.request.id:
            # somebody else was faster
            return

        task.state = RUNNING
        session.add(task)
        session.commit()
        celery_task_id = task.job_id
        _process_task_node(task, celery_task_id, pipeline_id, node_id)

        next_task_nodes = list(graph.successors(node_id))
    else:
        next_task_nodes = find_entry_point(graph)

    self.update_state(state=SUCCESS)

    for node_id in next_task_nodes:
        task = celery.send_task('mytasks.pipeline', args=(pipeline_id, node_id), kwargs={})
