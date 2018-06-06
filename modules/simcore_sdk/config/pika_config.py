""" Basic configuration file for pika

"""

from os import environ as env
import pika

RABBITMQ_USER = env.get('RABBITMQ_USER','simcore')
RABBITMQ_PASSWORD = env.get('RABBITMQ_PASSWORD','simcore')
RABBITMQ_LOG_CHANNEL = env.get('RABBITMQ_LOG_CHANNEL','comp.backend.channels.log')
RABBITMQ_PROGRESS_CHANNEL = env.get('RABBITMQ_PROGRESS_CHANNEL','comp.backend.channels.progress')
RABBITMQ_HOST="rabbit"
RABBITMQ_PORT=5672


class Config():
    def __init__(self):
        self._pika_credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
        self._pika_parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, 
            port=RABBITMQ_PORT, credentials=self._pika_credentials, connection_attempts=100)

        self._log_channel = RABBITMQ_LOG_CHANNEL
        self._progress_channel = RABBITMQ_PROGRESS_CHANNEL

    @property
    def parameters(self):
        return self._pika_parameters

    @property
    def log_channel(self):
        return self._log_channel

    @property
    def progress_channel(self):
        return self._progress_channel