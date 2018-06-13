import json
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import logging

import docker
import pika
from celery import Celery
from celery.states import SUCCESS as CSUCCESS
from sqlalchemy import and_, create_engine, exc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.attributes import flag_modified

from simcore_sdk.config.db import Config as db_config
from simcore_sdk.config.docker import Config as docker_config
from simcore_sdk.config.rabbit import Config as rabbit_config
from simcore_sdk.config.s3 import Config as s3_config
from simcore_sdk.models.pipeline_models import (RUNNING, SUCCESS,
                                    ComputationalPipeline,
                                    ComputationalTask)
from s3wrapper.s3_client import S3Client
from celery.utils.log import get_task_logger

rabbit_config = rabbit_config()
celery= Celery(rabbit_config.name, broker=rabbit_config.broker, backend=rabbit_config.backend)


logging.basicConfig(level=logging.DEBUG)
#_LOGGER = logging.getLogger(__name__)
_LOGGER = get_task_logger(__name__)
_LOGGER.setLevel(logging.DEBUG)


def _delete_contents(folder):
    for file in os.listdir(folder):
        file_path = os.path.join(folder, file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path): 
                shutil.rmtree(file_path)
        except (OSError, IOError) as _e:
            logging.exception("Could not delete files")

def _find_entry_point(G):
    result = []
    for node in G.nodes:
        if len(list(G.predecessors(node))) == 0:
            result.append(node)
    return result

class Sidecar(object):
    def __init__(self):
        # publish subscribe config
        self._pika_config = rabbit_config
        self._pika_parameters = self._pika_config.parameters
        self._pika_log_channel = self._pika_config.log_channel
        self._pika_progress_channel = self._pika_config.progress_channel

        # docker client config
        self._docker_config = docker_config()
        self.docker_client = docker.from_env(version='auto')
        self.docker_registry = self._docker_config.registry
        self.docker_registry_user = self._docker_config.user
        self.docker_registry_pwd = self._docker_config.pwd
        self.docker_image_name = ""
        self.docker_image_tag = ""
        self.docker_env = []

        # object storage config
        self._s3_config = s3_config()
        self.s3_client = S3Client(endpoint=self._s3_config.endpoint,
            access_key=self._s3_config.access_key, secret_key=self._s3_config.secret_key)
        self.s3_bucket = self._s3_config.bucket_name
        self.s3_client.create_bucket(self.s3_bucket)

        # db config
        self._db_config = db_config()
        self.db = create_engine(self._db_config.endpoint, client_encoding='utf8')
        self.Session = sessionmaker(self.db)
        self.session = self.Session()

        # thread pool
        self.pool = ThreadPoolExecutor(1)

        # current task
        self.task = None
        self.run_pool = False

        # shared folders
        self.shared_input_folder = ""
        self.shared_output_folder = ""
        self.shared_log_folder = ""

    def _create_shared_folders(self):
        for folder in [self.shared_input_folder, self.shared_log_folder, self.shared_output_folder]:
            if not os.path.exists(folder):
                os.makedirs(folder)
            else:
                _delete_contents(folder)

    def _process_task_input(self):
        """ Writes input key-value pairs into a dictionary

            if the value of any port starts with 'link.' the corresponding
            output ports a fetched or files dowloaded --> @ jsonld

            The dictionary is dumped to input.json, files are dumped
            as port['key']. Both end up in /input/ of the container
        """
        _input = self.task.input
        _LOGGER.debug('Input parsing for {} and node {} from container'.format(self.task.pipeline_id, self.task.internal_id))
        _LOGGER.debug(_input)

        input_ports = dict()
        for port in _input:
            _LOGGER.debug(port)
            port_name = port['key']
            port_value = port['value']
            _LOGGER.debug(type(port_value))
            if isinstance(port_value, str) and port_value.startswith("link."):
                if port['type'] == 'file-url':
                    _LOGGER.debug('Fetch S3 {}'.format(port_value))
                    object_name = os.path.join(str(self.task.pipeline_id),*port_value.split(".")[1:])
                    input_file = os.path.join(self.shared_input_folder, port_name)
                    _LOGGER.debug('Downlaoding from  S3 {}/{}'.format(self.s3_bucket, object_name))
                    #if self.s3_client.exists_object(self.s3_bucket, object_name, True):
                    success = False
                    ntry = 3
                    trial = 0
                    while not success and trial < ntry:
                        _LOGGER.debug('Downloading to {} trial {} from {}'.format(input_file, trial, ntry))
                        success = self.s3_client.download_file(self.s3_bucket, object_name, input_file)
                        trial = trial + 1
                    if success:
                        input_ports[port_name] = port_name
                        _LOGGER.debug("DONWLOAD successfull {}".format(port_name))
                    else:
                        _LOGGER.debug("ERROR, input port {} not found in S3".format(object_name))
                        input_ports[port_name] = None
                else:
                    _LOGGER.debug('Fetch DB {}'.format(port_value))                    
                    other_node_id = port_value.split(".")[1] 
                    other_output_port_id = port_value.split(".")[2]
                    other_task = self.session.query(ComputationalTask).filter(and_(ComputationalTask.node_id==other_node_id,
                                            ComputationalTask.pipeline_id==self.task.pipeline_id)).one()
                    if other_task is None:
                        _LOGGER.debug("ERROR, input port {} not found in db".format(port_value))
                    else:
                        for oport in other_task.output:
                            if oport['key'] == other_output_port_id:
                                input_ports[port_name] = oport['value']
        #dump json file
        if len(input_ports):
            file_name = os.path.join(self.shared_input_folder, 'input.json')
            with open(file_name, 'w') as f:
                json.dump(input_ports, f)

    def _pull_image(self):
        self.docker_client.login(registry=self.docker_registry,
            username=self.docker_registry_user, password=self.docker_registry_pwd)
        
        self.docker_client.images.pull(self.docker_image_name, tag=self.docker_image_tag)

    def _bg_job(self, task, log_file):
        connection = pika.BlockingConnection(self._pika_parameters)

        channel = connection.channel()
        channel.exchange_declare(exchange=self._pika_log_channel, exchange_type='fanout')
        channel.exchange_declare(exchange=self._pika_progress_channel, exchange_type='fanout')

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
                        channel.basic_publish(exchange=self._pika_progress_channel, routing_key='', body=prog_body)
                    else:
                        log_data = {"Channel" : "Log", "Node": task.internal_id, "Message" : clean_line}
                        log_body = json.dumps(log_data)
                        channel.basic_publish(exchange=self._pika_log_channel, routing_key='', body=log_body)


        connection.close()

    def _process_task_output(self):
        """ There will be some files in the /output
        
                - Maybe a output.json (should contain key value for simple things)
                - other files: should be named by the key in the output port

            Files will be pushed to S3 with reference in db. output.json will be parsed
            and the db updated
        """
        directory = self.shared_output_folder
        if not os.path.exists(directory):
            return
        try:
            for root, _dirs, files in os.walk(directory):
                for name in files:
                    filepath = os.path.join(root, name)
                    # the name should match what is in the db!

                    if name == 'output.json':
                        _LOGGER.debug("POSTRO FOUND output.json")
                        # parse and compare/update with the tasks output ports from db
                        output_ports = dict()                        
                        with open(filepath) as f:
                            output_ports = json.load(f)
                            task_outputs = self.task.output
                            for to in task_outputs:
                                if to['key'] in output_ports.keys():
                                    to['value'] = output_ports[to['key']]
                                    _LOGGER.debug("POSTRPO to['value]' becomes{}".format(output_ports[to['key']]))
                                    flag_modified(self.task, "output")
                                    self.session.commit()
                    else:
                        object_name = str(self.task.pipeline_id) + "/" + self.task.node_id + "/" + name
                        success = False
                        ntry = 3
                        trial = 0
                        while not success and trial < ntry:
                            _LOGGER.debug("POSTRO pushes to S3 {}, try {} from {}".format(object_name, ntry, trial))
                            success = self.s3_client.upload_file(self.s3_bucket, object_name, filepath)
                            trial = trial + 1

        except (OSError, IOError) as _e:
            logging.exception("Could not process output")

    def _process_task_log(self):
        """ There will be some files in the /log
                
                - put them all into S3 /log
        """
        directory = self.shared_log_folder
        if os.path.exists(directory):
            for root, _dirs, files in os.walk(directory):
                for name in files:
                    filepath = os.path.join(root, name)
                    object_name = str(self.task.pipeline_id) + "/" + self.task.node_id + "/log/" + name
                    if not self.s3_client.upload_file(self.s3_bucket, object_name, filepath):
                        _LOGGER.error("Error uploading file to S3")

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
        _LOGGER.debug('Pre-Processing Pipeline {} and node {} from container'.format(self.task.pipeline_id, self.task.internal_id))
        self._create_shared_folders()
        self._process_task_input()
        self._pull_image()
       
    def process(self):
        _LOGGER.debug('Processing Pipeline {} and node {} from container'.format(self.task.pipeline_id, self.task.internal_id))

        self.run_pool = True

        # touch output file
        log_file = os.path.join(self.shared_log_folder, "log.dat")

        Path(log_file).touch()
        fut = self.pool.submit(self._bg_job, self.task, log_file)

        try:
            docker_image = self.docker_image_name + ":" + self.docker_image_tag 
            self.docker_client.containers.run(docker_image, "run", 
                 detach=False, remove=True,
                 volumes = {'services_input'  : {'bind' : '/input'}, 
                            'services_output' : {'bind' : '/output'},
                            'services_log'    : {'bind'  : '/log'}},
                 environment=self.docker_env)
        except docker.errors.ContainerError as _e:
            _LOGGER.error("Run container returned non zero exit code")
        except docker.errors.ImageNotFound as _e:
            _LOGGER.error("Run container: Image not found")
        except docker.errors.APIError as _e:
            _LOGGER.error("Run Container: Server returns error")


        time.sleep(1)
        self.run_pool = False
        while not fut.done():
            time.sleep(0.1)

        _LOGGER.debug('DONE Processing Pipeline {} and node {} from container'.format(self.task.pipeline_id, self.task.internal_id))

    def run(self):
        self.preprocess()
        self.process()
        self.postprocess()

    def postprocess(self):
        _LOGGER.debug('Post-Processing Pipeline {} and node {} from container'.format(self.task.pipeline_id, self.task.internal_id))
        
        self._process_task_output()
        self._process_task_log()

        self.task.state = SUCCESS
        self.session.add(self.task)
        self.session.commit()

        _LOGGER.debug('DONE Post-Processing Pipeline {} and node {} from container'.format(self.task.pipeline_id, self.task.internal_id))
        

    def _is_node_ready(self, task, graph):
        tasks = self.session.query(ComputationalTask).filter(and_(
            ComputationalTask.node_id.in_(list(graph.predecessors(task.node_id))),
            ComputationalTask.pipeline_id==task.pipeline_id)).all()

        _LOGGER.debug("TASK {} ready? Checking ..".format(task.internal_id))
        for dep_task in tasks:
            job_id = dep_task.job_id
            if not job_id:
                return False
            else:
                _LOGGER.debug("TASK {} DEPENDS ON {} with stat {}".format(task.internal_id, dep_task.internal_id,dep_task.state))
                if not dep_task.state == SUCCESS:
                    return False
        _LOGGER.debug("TASK {} is ready".format(task.internal_id))

        return True

    def inspect(self, celery_task, pipeline_id, node_id):
        _pipeline = self.session.query(ComputationalPipeline).filter_by(pipeline_id=pipeline_id).one()
        graph = _pipeline.execution_graph
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
                _LOGGER.error(err)  
                # no result found, just return
                return next_task_nodes

            if task == None:
                return next_task_nodes
    
            # already done or running and happy
            if task.job_id and (task.state == SUCCESS or task.state == RUNNING):
                _LOGGER.debug("TASK {} ALREADY DONE OR RUNNING".format(task.internal_id))
                do_process = False

            # Check if node's dependecies are there
            if not self._is_node_ready(task, graph):
                _LOGGER.debug("TASK {} NOT YET READY".format(task.internal_id))
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
            next_task_nodes = _find_entry_point(graph)

        celery_task.update_state(state=CSUCCESS)
        
        return next_task_nodes

SIDECAR = Sidecar()
@celery.task(name='comp.task', bind=True)
def pipeline(self, pipeline_id, node_id=None):
    next_task_nodes = SIDECAR.inspect(self, pipeline_id, node_id)
    for _node_id in next_task_nodes:
        _task = celery.send_task('comp.task', args=(pipeline_id, _node_id), kwargs={})
