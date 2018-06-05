"""
    Uses socketio and aiohtttp framework
"""
# pylint: disable=C0103

from aiohttp import web
import aiohttp
import asyncio
import async_timeout
import uuid
import json
import datetime

from setup import *

comp_backend_routes = web.RouteTableDef()

async def async_request(method, session, url, json=None, timeout=10):
    async with async_timeout.timeout(timeout):
        if method == "GET":
            async with session.get(url) as response:
                return await response.json()
        elif method == "POST":
            async with session.post(url, json=json) as response:
                return await response.json()

@comp_backend_routes.post('/start_pipeline')
async def start_pipeline(request):
    """
    ---
    description: This end-point starts a computational pipeline.
    tags:
    - computational backend
    produces:
    - application/json
    responses:
        "200":
            description: successful operation. Return "pong" text
        "405":
            description: invalid HTTP Method
    """

    request_data = await request.json()

    _id = request_data['pipeline_mockup_id']

    with open('mockup.json') as f:
        mockup = json.load(f)

    nodes = mockup['nodes']
    links = mockup['links']

    dag_adjacency_list = dict()
    tasks = dict()
    for node in nodes:
        node_id = node['uuid']
        # find connections
        successor_nodes = []
        task = {}
        task["input"] = node["inputs"]
        task["output"] = node["outputs"]
        task["image"] = { "name" : "masu.speag.com/simcore/services/comp/sleeper",
                          "tag"  : "1.0"}

        for link in links:
            if link['node1Id'] == node_id:
                successor_node_id = link['node2Id']
                if successor_node_id not in successor_nodes:
                    successor_nodes.append(successor_node_id)
            if link['node2Id'] == node_id:
                # there might be something coming in
                predecessor_node_id = link['node1Id']
                output_port = link['port1Id']            
                input_port = link['port2Id']
                # we use predecessor_node_id.output_port as id fo the input
                for t in task['input']:
                    if t['key'] == input_port:
                        t['value'] = 'link.' + predecessor_node_id + "." + output_port


        if len(successor_nodes):
            dag_adjacency_list[node_id] = successor_nodes
        tasks[node_id] = task

    pipeline = ComputationalPipeline(dag_adjacency_list=dag_adjacency_list, state=0)

    session.add(pipeline)
    session.flush()

    pipeline_id = pipeline.pipeline_id
    pipeline_name = "mockup"
    internal_id = 1

    for node_id in tasks:
        task = tasks[node_id]
        new_task = ComputationalTask(pipeline_id=pipeline_id, node_id=node_id, internal_id=internal_id, image=task['image'],
                    input=task['input'], output=task['output'], submit=datetime.datetime.utcnow())
        internal_id = internal_id+1
        session.add(new_task)

    session.commit()
    
    task = celery.send_task('mytasks.pipeline', args=(pipeline_id,), kwargs={})

    response = {}
    response['pipeline_name'] = pipeline_name
    response['pipeline_id'] = str(pipeline_id)

    return web.json_response(response)