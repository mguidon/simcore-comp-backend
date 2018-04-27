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

    id = request_data['pipeline_mockup_id']

    #  ccreate some fake data for now
    data = {}
    data['pipeline_name'] = "My Pipeline"
    node_ids = []
    for _ in range(8):
        node_ids.append(str(uuid.uuid4()))

    data['nodes'] = node_ids

    dag_adjacency_list = dict()
    dag_adjacency_list[node_ids[0]] = [node_ids[2]]
    dag_adjacency_list[node_ids[1]] = [node_ids[3]]
    dag_adjacency_list[node_ids[2]] = [node_ids[4]]
    dag_adjacency_list[node_ids[3]] = [node_ids[4]]
    dag_adjacency_list[node_ids[4]] = [node_ids[5], node_ids[6]]
    dag_adjacency_list[node_ids[5]] = [node_ids[7]]
    dag_adjacency_list[node_ids[6]] = [node_ids[7]]

    data['dag'] = dag_adjacency_list

     # try to parse data
    pipeline_name = data['pipeline_name']
    nodes = data['nodes']
    dag_adjacency_list = data['dag']
 
    pipeline = ComputationalPipeline(dag_adjacency_list=dag_adjacency_list,
        state=0)

    session.add(pipeline)
    session.flush()

    pipeline_id = pipeline.pipeline_id

    internal_id = 1
    for node_id in nodes:
        new_task = ComputationalTask(pipeline_id=pipeline_id, node_id=node_id, internal_id=internal_id)
        internal_id = internal_id+1
        session.add(new_task)

    session.commit()

    task = celery.send_task('mytasks.pipeline', args=(pipeline_id,), kwargs={})

    response = {}
    response['pipeline_name'] = pipeline_name
    response['pipeline_id'] = str(uuid.uuid4())

    log = "asdfasdfasdf"
    await sio.emit("logger", data = log)
    
    return web.json_response(response)