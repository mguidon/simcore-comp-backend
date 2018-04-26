import celery.states as states
import requests
import uuid
import json
import os
from celery.result import AsyncResult
from flask import Flask, request, abort, jsonify

from worker import celery

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pipeline_models import ComputationalPipeline, ComputationalTask, Base

env = os.environ

POSTGRES_URL = "postgres:5432"
POSTGRES_USER = env.get("POSTGRES_USER", "simcore")
POSTGRES_PW = env.get("POSTGRES_PASSWORD", "simcore")
POSTGRES_DB = env.get("POSTGRES_DB", "simcoredb")

DB_URL = 'postgresql+psycopg2://{user}:{pw}@{url}/{db}'.format(user=POSTGRES_USER, pw=POSTGRES_PW, url=POSTGRES_URL, db=POSTGRES_DB)

db = create_engine(DB_URL, client_encoding='utf8')

Session = sessionmaker(db)
session = Session()

Base.metadata.create_all(db)

app = Flask(__name__)

@app.route('/stop_pipeline')
def stop_pipeline():
    return "Pipeline stopped"

@app.route('/start_pipeline', methods=['POST'])
def start_pipeline():
    if not request.json:
        abort(400)
    
    # try to parse data
    data = request.json
    pipeline_name = data['pipeline_name']
    nodes = data['nodes']
    dag_adjacency_list = data['dag']

   
    #return "Pipeline {} started with id {}".format(name, pipeline_id)
   
    pipeline = ComputationalPipeline(dag_adjacency_list=dag_adjacency_list,
        state=0)

    session.add(pipeline)
    session.flush()

    pipeline_id = pipeline.pipeline_id

    for node_id in nodes:
        new_task = ComputationalTask(pipeline_id=pipeline_id, node_id=node_id)
        session.add(new_task)

    session.commit()

    #task = celery.send_task('mytasks.pipeline', args=(pipeline.id,), kwargs={})

    response = {}
    response['pipeline_name'] = pipeline_name
    response['pipeline_id'] = pipeline_id

    return jsonify(response)

@app.route("/calc", methods=['GET'])
def calc():
    #ata = request.get_json()
   
    data_str = """{
    "input": 
    [
           {
           	"name": "N", 
               	"value": 10
           }, 
           {
           	"name": "xmin", 
               	"value": -1.0
           }, 
           {
           	"name": "xmax", 
               	"value": 1.0
           },
           {
               	"name": "func", 
               	"value": "exp(x)*sin(x)"
           }
    ],
    "container":
    {
    	"name": "masu.speag.com/comp.services/sidecar-solver",
        "tag": "1.1"
    }
    }"""

    data = json.loads(data_str)
    task = celery.send_task('mytasks.run', args=[data], kwargs={})
         
    return "submitted"

if __name__ == "__main__":
    app.run(port=8010, debug=True, host='0.0.0.0', threaded=True)
