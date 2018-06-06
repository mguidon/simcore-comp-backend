""" Basic configuration file for rabbitMQ

"""

from os import environ as env

RABBITMQ_USER = env.get('RABBITMQ_USER','simcore')
RABBITMQ_PASSWORD = env.get('RABBITMQ_PASSWORD','simcore')
RABBITMQ_HOST="rabbit"
RABBITMQ_PORT=5672

AMQ_URL = 'amqp://{user}:{pw}@{url}:{port}'.format(user=RABBITMQ_USER, pw=RABBITMQ_PASSWORD, url=RABBITMQ_HOST, port=RABBITMQ_PORT)

CELERY_BROKER_URL = AMQ_URL
CELERY_RESULT_BACKEND=env.get('CELERY_RESULT_BACKEND','rpc://')

class Config():
    def __init__(self):
        self._broker_url = CELERY_BROKER_URL
        self._result_backend = CELERY_RESULT_BACKEND
        self._module_name = "tasks"
    
    def broker(self):
        return self._broker_url

    def backend(self):
        return self._result_backend

    def name(self):
        return self._module_name