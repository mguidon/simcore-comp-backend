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
from sqlalchemy import and_, exc, create_engine
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

POSTGRES_URL = "postgres:5432"
POSTGRES_USER = env.get("POSTGRES_USER", "simcore")
POSTGRES_PW = env.get("POSTGRES_PASSWORD", "simcore")
POSTGRES_DB = env.get("POSTGRES_DB", "simcoredb")

DB_URL = 'postgresql+psycopg2://{user}:{pw}@{url}/{db}'.format(user=POSTGRES_USER, pw=POSTGRES_PW, url=POSTGRES_URL, db=POSTGRES_DB)

S3_ENDPOINT = env.get("S3_ENDPOINT", "")
S3_ACCESS_KEY = env.get("S3_ACCESS_KEY", "")
S3_SECRET_KEY = env.get("S3_SECRET_KEY", "")
S3_BUCKET_NAME = env.get("S3_BUCKET_NAME", "")


class Sidecar(object):
    def __init__(self):
        # publish subscribe config
        self._pika_credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
        self._pika_parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, 
            port=RABBITMQ_PORT, credentials=self._pika_credentials, connection_attempts=100)

        # docker client config
        self.docker_client = docker.from_env(version='auto')
        self.docker_registry = "masu.speag.com/v2"
        self.docker_registry_user = "z43"
        self.docker_registry_pwd = "z43"

        # object storage config
        self.s3_client = S3Client(endpoint=S3_ENDPOINT, access_key=S3_ACCESS_KEY, secret_key=S3_SECRET_KEY)
        self.s3_client.create_bucket(S3_BUCKET_NAME)

        # db config
        self.db = create_engine(DB_URL, client_encoding='utf8')
        self.Session = sessionmaker(self.db)
        self.session = self.Session()

        # thread pool
        self.pool = ThreadPoolExecutor(1)

        self.task = None
        

    def _delete_contents(self, folder):
        for file in os.listdir(folder):
            file_path = os.path.join(folder, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path): shutil.rmtree(file_path)
            except Exception as e:
                print(e)

    def _create_shared_folders(self):
        for folder in [self.shared_input_folder, self.shared_log_folder, self.shared_output_folder]:
            if not os.path.exists(folder):
                os.makedirs(folder)
            else:
                self._delete_contents(folder)

    def _parse_input(self):
        input = self.task.input


    def _pull_image(self):
        self.docker_client.login(registry=self.docker_registry,
            username=self.docker_registry_user, password=self.docker_registry_pwd)
        
        self.docker_client.images.pull(self.docker_image_name, tag=self.docker_image_tag)

    def _bg_job(self, task, log_file):
        connection = pika.BlockingConnection(self._pika_parameters)

        channel = connection.channel()
        channel.exchange_declare(exchange=RABBITMQ_LOG_CHANNEL, exchange_type='fanout')
        channel.exchange_declare(exchange=RABBITMQ_PROGRESS_CHANNEL, exchange_type='fanout')

        with open(log_file) as file_:
            # Go to the end of file
            file_.seek(0,2)
            while self.run_pool:
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

    def _process_task_output(self):
        directory = self.shared_output_folder
        if not os.path.exists(directory):
            return
        try:
            for root, _dirs, files in os.walk(directory):
                for name in files:
                    filepath = os.path.join(root, name)
                    object_name = str(self.task.pipeline_id) + "/" + self.task.job_id + "/" + name
                    self.s3_client.upload_file(S3_BUCKET_NAME, object_name, filepath)

        except:
            import traceback
            traceback.print_exc()
            return -2

    def initialize(self, task):
        self.task = task
        self.docker_image_name = task.image['name']
        self.docker_image_tag = task.image['tag']
        self.shared_input_folder = os.path.join("/", "input", task.job_id)
        self.shared_output_folder = os.path.join("/", "output", task.job_id)
        self.shared_log_folder = os.path.join("/", "log", task.job_id)

        self.docker_env = ["INPUT_FOLDER=" + self.shared_input_folder,
                           "OUTPUT_FOLDER=" + self.shared_output_folder,
                           "LOG_FOLDER=" + self.shared_log_folder]


    def preprocess(self):
        print('Pre-Processing Pipeline {} and node {} from container'.format(self.task.pipeline_id, self.task.internal_id))
        self._create_shared_folders()
        #self._parse_input()
        self._pull_image()
       
    def process(self):
        print('Processing Pipeline {} and node {} from container'.format(self.task.pipeline_id, self.task.internal_id))

        self.run_pool = True

        # touch output file
        log_file = os.path.join(self.shared_log_folder, "log.dat")

        Path(log_file).touch()
        fut = self.pool.submit(self._bg_job, self.task, log_file)

        try:
            docker_image = self.docker_image_name + ":" + self.docker_image_tag 
            self.docker_client.containers.run(docker_image, "run", 
                 detach=False, remove=True,
                 volumes = {'simcorecompbackend_input'  : {'bind' : '/input'}, 
                            'simcorecompbackend_output' : {'bind' : '/output'},
                            'simcorecompbackend_log'    : {'bind'  : '/log'}},
                 environment=self.docker_env)
        except Exception as e:
            print(e)

        time.sleep(1)
        self.run_pool = False
        while not fut.done():
            time.sleep(0.1)

        print('DONE Processing Pipeline {} and node {} from container'.format(self.task.pipeline_id, self.task.internal_id))

    def run(self):
        self.preprocess()
        self.process()
        self.postprocess()

    def postprocess(self):
        print('Post-Processing Pipeline {} and node {} from container'.format(self.task.pipeline_id, self.task.internal_id))
        
        self._process_task_output()
        self.task.state = SUCCESS
        self.session.add(self.task)
        self.session.commit()

        print('DONE Post-Processing Pipeline {} and node {} from container'.format(self.task.pipeline_id, self.task.internal_id))
        

    def _find_entry_point(self, G):
        result = []
        for node in G.nodes:
            if len(list(G.predecessors(node))) == 0:
                result.append(node)
        return result

    def _is_node_ready(self, task, graph):
        tasks = self.session.query(ComputationalTask).filter(and_(
            ComputationalTask.node_id.in_(list(graph.predecessors(task.node_id))),
            ComputationalTask.pipeline_id==task.pipeline_id)).all()

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

    def inspect(self, celery_task, pipeline_id, node_id):

        pipeline = self.session.query(ComputationalPipeline).filter_by(pipeline_id=pipeline_id).one()
        graph = pipeline.execution_graph
        next_task_nodes = []
        if node_id:
            do_process = True
            # find the for the current node_id, skip if there is already a job_id around
            query = self.session.query(ComputationalTask).filter(and_(ComputationalTask.node_id==node_id,
                ComputationalTask.pipeline_id==pipeline_id, ComputationalTask.job_id==None))
            # Use SELECT FOR UPDATE TO lock the row
            query.with_for_update()
            try:
                task = query.one()
            except exc.SQLAlchemyError as err:
                print(err)  
                # no result found, just return
                return next_task_nodes

            if task == None:
                return next_task_nodes
    
            # already done or running and happy
            if task.job_id and (task.state == SUCCESS or task.state == RUNNING):
                print("TASK {} ALREADY DONE OR RUNNING".format(task.internal_id))
                do_process = False

            # Check if node's dependecies are there
            if not self._is_node_ready(task, graph):
                print("TASK {} NOT YET READY".format(task.internal_id))
                do_process = False

            if do_process:           
                task.job_id = celery_task.request.id
                self.session.add(task)
                self.session.commit()
            else:
                return next_task_nodes

            task = self.session.query(ComputationalTask).filter(
                and_(ComputationalTask.node_id==node_id,ComputationalTask.pipeline_id==pipeline_id)).one()
            if task.job_id != celery_task.request.id:
                # somebody else was faster
                return next_task_nodes

            task.state = RUNNING
            self.session.add(task)
            self.session.commit()
            self.initialize(task)
            self.run()

            next_task_nodes = list(graph.successors(node_id))
        else:
            next_task_nodes = self._find_entry_point(graph)

        celery_task.update_state(state=SUCCESS)
        
        return next_task_nodes

SIDECAR = Sidecar()
@celery.task(name='mytasks.pipeline', bind=True)
def pipeline(self, pipeline_id, node_id=None):
    next_task_nodes = SIDECAR.inspect(self, pipeline_id, node_id)
    for node_id in next_task_nodes:
        _task = celery.send_task('mytasks.pipeline', args=(pipeline_id, node_id), kwargs={})
        else:
            next_task_nodes = self._find_entry_point(graph)

        celery_task.update_state(state=SUCCESS)
        
        return next_task_nodes

SIDECAR = Sidecar()
@celery.task(name='mytasks.pipeline', bind=True)
def pipeline(self, pipeline_id, node_id=None):
    next_task_nodes = SIDECAR.inspect(self, pipeline_id, node_id)
    for node_id in next_task_nodes:
        _task = celery.send_task('mytasks.pipeline', args=(pipeline_id, node_id), kwargs={})

            next_task_nodes = list(graph.successors(node_id))
        else:
            next_task_nodes = self._find_entry_point(graph)

        celery_task.update_state(state=SUCCESS)
        
        return next_task_nodes

SIDECAR = Sidecar()
@celery.task(name='mytasks.pipeline', bind=True)
def pipeline(self, pipeline_id, node_id=None):
    next_task_nodes = SIDECAR.inspect(self, pipeline_id, node_id)
    for node_id in next_task_nodes:
        _task = celery.send_task('mytasks.pipeline', args=(pipeline_id, node_id), kwargs={})
