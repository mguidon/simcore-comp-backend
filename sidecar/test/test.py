import docker
import os
import shutil
from pathlib import Path

io_dirs = {}

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
        dir = os.path.join("./", d, task_id)
        io_dirs[d] = dir
        if not os.path.exists(dir):
            os.makedirs(dir)

    log_file = os.path.join(io_dirs['log'], "log.dat")
    #Path(log_file).touch()

def start_container(docker_image_name, io_env):

    client = docker.from_env(version='auto') 
    # touch output fil
    try:
        client.containers.run(docker_image_name, "run", 
             detach=False, remove=True,
             volumes = {'/home/guidon/devel/simcore-comp-backend/sidecar/test/input'  : {'bind' : '/input'}, 
                        '/home/guidon/devel/simcore-comp-backend/sidecar/test/output' : {'bind' : '/output'},
                        '/home/guidon/devel/simcore-comp-backend/sidecar/test/log'    : {'bind'  : '/log'}},
             environment=io_env)
    except Exception as e:
        print(e)

def _process():
    task_id = "123"
    # create directories
    create_directories(task_id)
    # fetch container

    # image_name = "masu.speag.com/simcore/services/comp/sleeper"
    # image_tag = "1.0"
    # client = docker.from_env(version='auto')
    # client.login(registry="masu.speag.com/v2", username="z43", password="z43")
    # client.images.pull(image_name, tag=image_tag

    image_name = 'sleeper'
    image_tag = 'latest'
    docker_image_name = image_name + ":" + image_tag
    io_env = []
    io_env.append("INPUT_FOLDER=/input/"+task_id)
    io_env.append("OUTPUT_FOLDER=/output/"+task_id)
    io_env.append("LOG_FOLDER=/log/"+task_id)
    start_container(docker_image_name, io_env)


_process()