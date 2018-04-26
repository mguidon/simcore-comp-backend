import hashlib
import json
import os
import shutil
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import docker
import requests
from celery import Celery
from celery.result import AsyncResult
from celery.signals import (after_setup_logger, task_failure, task_postrun,
                            task_prerun)
from celery.states import SUCCESS


env=os.environ
RABBITMQ_USER = env.get('RABBITMQ_USER','simcore')
RABBITMQ_PASSWORD = env.get('RABBITMQ_PASSWORD','simcore')
AMQ_URL = 'amqp://{user}:{pw}@{url}:{port}'.format(user=RABBITMQ_USER, pw=RABBITMQ_PASSWORD, url='rabbit',port=5672)

CELERY_BROKER_URL = AMQ_URL #env.get('CELERY_BROKER_URL','amqp://z43:z43@rabbit:5672'),
#MYSQL CELERY_RESULT_BACKEND=env.get('CELERY_RESULT_BACKEND','db+' + DATABASE_URI)
CELERY_RESULT_BACKEND=env.get('CELERY_RESULT_BACKEND','rpc://')

celery= Celery('tasks',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND)


io_dirs = {}
pool = ThreadPoolExecutor(1)
run_pool = True

#REDIS r = redis.StrictRedis(host="redis", port=6379)
#REDIS r.flushall()
#REDIS r.set('count', 0)
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

#MYSQL engine = create_engine(DATABASE_URI)
#MYSQL Session = sessionmaker(bind=engine)

def find_entry_point(G):
    result = []
    for node in G.nodes:
        if len(list(G.predecessors(node))) == 0:
            result.append(node)
    return result

@task_prerun.connect
def prerun(*args, **kwargs):
    pass
#MYSQL    global session
#MYSQL    session = Session()


@task_postrun.connect
def postrun(*args, **kwargs):
    pass
#MYSQL    session.flush()
#MYSQL   session.close()

def _is_node_rdy(task, graph):
#MYSQL    tasks = session.query(Task).filter(Task.id.in_(list(graph.predecessors(task.id)))).all()
#MYSQL    for dep_task in tasks:
#MYSQL        if not dep_task.celery_task_uid or \
#MYSQL           not AsyncResult(dep_task.celery_task_uid).state == SUCCESS:
#MYSQL            return False
    return True

def _process_task_node(celery_task, task, task_id, workflow_id, cur_task_id):
    task.celery_task_uid = task_id
#MYSQL    session.add(task)
#MYSQL    session.commit()
    log_key = task_id + ":log"
    prog_key = task_id + ":progress"
    #r.rpush(log_key, 'Runnning Workflow {} and Task {} via redis'.format(workflow_id, cur_task_id).encode('utf-8'))
    # simulate that task runs
    dp = 1.0 / (task.sleep-1)
    for i in range(task.sleep):
        print('{}: Sleep, sec: {}'.format(task_id, i))
#REDIS        r.rpush(log_key, '{}: Sleep, sec: {} of {}'.format(cur_task_id, i+1, task.sleep))
        process_percent = i * dp 
#REDIS        r.set(prog_key, str(process_percent).encode('utf-8'))
        time.sleep(1)
    
@celery.task(name='mytasks.pipeline', bind=True)
def pipeline(self, workflow_id, cur_task_id=None):
    pass
#MYSQL    workflow = session.query(Workflow).filter_by(id=workflow_id).one()
#MYSQL    graph = workflow.execution_graph
#MYSQL    next_task_ids = []
#MYSQL    if cur_task_id:
#MYSQL        task = session.query(Task).get(cur_task_id)
#MYSQL
#MYSQL        if task.celery_task_uid and AsyncResult(task.celery_task_uid).state == SUCCESS:
#MYSQL            print("NOPE 0", task.celery_task_uid, cur_task_id)
#MYSQL            return
#MYSQL
#MYSQL        if not _is_node_rdy(task, graph):
#MYSQL            print("NOPE 1")
#MYSQL            return
#MYSQL
#MYSQL        _process_task_node(self, task, self.request.id, workflow_id, cur_task_id)
#MYSQL
#MYSQL        next_task_ids = list(graph.successors(cur_task_id))
#MYSQL    else:
#MYSQL        next_task_ids = find_entry_point(graph)
#MYSQL
#MYSQL    self.update_state(state=SUCCESS)
#MYSQL
#MYSQL    for task_id in next_task_ids:
#MYSQL        task = celery.send_task('mytasks.pipeline', args=(workflow_id, task_id), kwargs={})
