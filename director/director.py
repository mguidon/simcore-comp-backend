import celery.states as states
import requests
import uuid
import json

from celery.result import AsyncResult
from flask import Flask, request, abort, jsonify

from worker import celery

app = Flask(__name__)

task_info = {}

@app.route('/stop_pipeline')
def stop_pipeline():
    return "Pipeline stopped"

@app.route('/start_pipeline', methods=['POST'])
def start_pipeline():
    if not request.json:
        abort(400)
    
    name = request.json['pipeline_name']
    pipeline_id = str(uuid.uuid4())
    # task = celery.send_task('mytasks.pipeline', args=(pipeline.id,), kwargs={})

    response = {}
    response['pipeline_name'] = name
    response['pipeline_id'] = pipeline_id

    #return "Pipeline {} started with id {}".format(name, pipeline_id)
   
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
