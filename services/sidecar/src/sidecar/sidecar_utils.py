import logging
import os
import shutil
import docker

from simcore_sdk.config.docker import Config as docker_config
from simcore_sdk.config.s3 import Config as s3_config
from s3wrapper.s3_client import S3Client
from simcore_sdk.config.rabbit import Config as rabbit_config


def delete_contents(folder):
    for _fname in os.listdir(folder):
        file_path = os.path.join(folder, _fname)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path): 
                shutil.rmtree(file_path)
        except (OSError, IOError):
            logging.exception("Could not delete files")

def find_entry_point(g):
    result = []
    for node in g.nodes:
        if len(list(g.predecessors(node))) == 0:
            result.append(node)
    return result

class DockerSettings(object):
    # pylint: disable=too-many-instance-attributes
    def __init__(self):
        self._config = docker_config()
        self.client = docker.from_env(version='auto')
        self.registry = self._config.registry
        self.registry_user = self._config.user
        self.registry_pwd = self._config.pwd
        self.image_name = ""
        self.image_tag = ""
        self.env = []


class S3Settings(object):
    def __init__(self):
        self._config = s3_config()
        self.client = S3Client(endpoint=self._config.endpoint,
            access_key=self._config.access_key, secret_key=self._config.secret_key)
        self.bucket = self._config.bucket_name
        self.client.create_bucket(self.bucket)


class RabbitSettings(object):
    def __init__(self):
        self._pika = rabbit_config()
        self.parameters = self._pika.parameters
        self.log_channel = self._pika.log_channel
        self.progress_channel = self._pika.progress_channel