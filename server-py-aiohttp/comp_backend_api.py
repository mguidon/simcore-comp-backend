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

    id = request_data['pipeline_mockup_id']

    #  ccreate some fake data for now
    data = {}
    data['pipeline_name'] = "My Pipeline"
    node_ids = []

    if id == 0:
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

    elif id == 1:
        for _ in range(15):
            node_ids.append(str(uuid.uuid4()))
    
        data['nodes'] = node_ids

        dag_adjacency_list = dict()
        dag_adjacency_list[node_ids[0]] = [node_ids[1]]
        dag_adjacency_list[node_ids[1]] = [node_ids[2]]
        dag_adjacency_list[node_ids[2]] = [node_ids[9]]
        dag_adjacency_list[node_ids[3]] = [node_ids[4]]
        dag_adjacency_list[node_ids[4]] = [node_ids[5]]
        dag_adjacency_list[node_ids[5]] = [node_ids[9]]
        dag_adjacency_list[node_ids[6]] = [node_ids[7]]
        dag_adjacency_list[node_ids[7]] = [node_ids[8]]
        dag_adjacency_list[node_ids[8]] = [node_ids[11]]
        dag_adjacency_list[node_ids[9]] = [node_ids[10]]
        dag_adjacency_list[node_ids[10]] =  [node_ids[13]]
        dag_adjacency_list[node_ids[11]] =  [node_ids[12]]
        dag_adjacency_list[node_ids[12]] =  [node_ids[13]]
        dag_adjacency_list[node_ids[13]] = [node_ids[14]]

    elif id == 2:
        for _ in range(42):
            node_ids.append(str(uuid.uuid4()))
    
        data['nodes'] = node_ids
        dag_adjacency_list = dict()
        dag_adjacency_list[node_ids[0]] = [node_ids[1]]
        dag_adjacency_list[node_ids[1]] = [node_ids[2]]
        dag_adjacency_list[node_ids[2]] = [node_ids[24]]
        dag_adjacency_list[node_ids[3]] = [node_ids[4]]
        dag_adjacency_list[node_ids[4]] = [node_ids[5]]
        dag_adjacency_list[node_ids[5]] = [node_ids[24]]
        dag_adjacency_list[node_ids[6]] = [node_ids[7]]
        dag_adjacency_list[node_ids[7]] = [node_ids[8]]
        dag_adjacency_list[node_ids[8]] = [node_ids[24]]
        dag_adjacency_list[node_ids[9]] = [node_ids[10]]
        dag_adjacency_list[node_ids[10]] = [node_ids[11]]
        dag_adjacency_list[node_ids[11]] = [node_ids[25]]
        dag_adjacency_list[node_ids[12]] = [node_ids[13]]
        dag_adjacency_list[node_ids[13]] = [node_ids[14]]
        dag_adjacency_list[node_ids[14]] = [node_ids[25]]
        dag_adjacency_list[node_ids[15]] = [node_ids[16]]
        dag_adjacency_list[node_ids[16]] = [node_ids[17]]
        dag_adjacency_list[node_ids[17]] = [node_ids[26]]
        dag_adjacency_list[node_ids[18]] = [node_ids[19]]
        dag_adjacency_list[node_ids[19]] = [node_ids[20]]
        dag_adjacency_list[node_ids[20]] = [node_ids[26]]
        dag_adjacency_list[node_ids[21]] = [node_ids[22]]
        dag_adjacency_list[node_ids[22]] = [node_ids[23]]
        dag_adjacency_list[node_ids[23]] = [node_ids[26]]
        dag_adjacency_list[node_ids[24]] = [node_ids[27]]
        dag_adjacency_list[node_ids[25]] = [node_ids[28],node_ids[29]]
        dag_adjacency_list[node_ids[26]] = [node_ids[30],node_ids[31],node_ids[32]]
        dag_adjacency_list[node_ids[27]] = [node_ids[34]]
        dag_adjacency_list[node_ids[28]] = [node_ids[34]]
        dag_adjacency_list[node_ids[29]] = [node_ids[33]]
        dag_adjacency_list[node_ids[30]] = [node_ids[33]]
        dag_adjacency_list[node_ids[31]] = [node_ids[36]]
        dag_adjacency_list[node_ids[32]] = [node_ids[37]]
        dag_adjacency_list[node_ids[33]] = [node_ids[39]]
        dag_adjacency_list[node_ids[34]] = [node_ids[35]]
        dag_adjacency_list[node_ids[35]] = [node_ids[39]]
        dag_adjacency_list[node_ids[37]] = [node_ids[38]]
        dag_adjacency_list[node_ids[38]] = [node_ids[39]]
        dag_adjacency_list[node_ids[39]] = [node_ids[40],node_ids[41]]
                    
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
        #new_task = ComputationalTask(pipeline_id=pipeline_id, node_id=node_id, internal_id=internal_id, submit=datetime.datetime.utcnow())
        new_task = ComputationalTask(pipeline_id=pipeline_id, node_id=node_id, internal_id=internal_id)
        internal_id = internal_id+1
        session.add(new_task)

    session.commit()

    task = celery.send_task('mytasks.pipeline', args=(pipeline_id,), kwargs={})

    response = {}
    response['pipeline_name'] = pipeline_name
    response['pipeline_id'] = str(pipeline_id)

    return web.json_response(response)