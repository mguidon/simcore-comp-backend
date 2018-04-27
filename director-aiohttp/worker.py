import os
from celery import Celery

env = os.environ
RABBITMQ_USER = env.get('RABBITMQ_USER','simcore')
RABBITMQ_PASSWORD = env.get('RABBITMQ_PASSWORD','simcore')
AMQ_URL = 'amqp://{user}:{pw}@{url}:{port}'.format(user=RABBITMQ_USER, pw=RABBITMQ_PASSWORD, url='rabbit',port=5672)

CELERY_BROKER_URL = AMQ_URL
CELERY_RESULT_BACKEND = env.get('CELERY_RESULT_BACKEND','rpc://')

celery = Celery('tasks',
    broker = CELERY_BROKER_URL,
    backend = CELERY_RESULT_BACKEND)
