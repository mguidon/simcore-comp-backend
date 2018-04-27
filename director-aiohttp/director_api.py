"""
    Uses socketio and aiohtttp framework
"""
# pylint: disable=C0103

from aiohttp import web
import aiohttp
import asyncio
import async_timeout
import json
import uuid

# from setup import *

director_routes = web.RouteTableDef()

async def async_request(method, session, url, json=None, timeout=10):
    async with async_timeout.timeout(timeout):
        if method == "GET":
            async with session.get(url) as response:
                return await response.json()
        elif method == "POST":
            async with session.post(url, json=json) as response:
                return await response.json()

@director_routes.post('/start_pipeline')
async def start_pipeline(request):
   
    # try to parse data
    data = await request.json()
    pipeline_name = data['pipeline_name']
    nodes = data['nodes']
    dag_adjacency_list = data['dag']
 
#    pipeline = ComputationalPipeline(dag_adjacency_list=dag_adjacency_list,
#        state=0)
#
#    session.add(pipeline)
#    session.flush()
#
#    pipeline_id = pipeline.pipeline_id
#
#    internal_id = 1
#    for node_id in nodes:
#        new_task = ComputationalTask(pipeline_id=pipeline_id, node_id=node_id, internal_id=internal_id)
#        internal_id = internal_id+1
#        session.add(new_task)
#
#    session.commit()
#
#    task = celery.send_task('mytasks.pipeline', args=(pipeline_id,), kwargs={})

    response = {}
    response['pipeline_name'] = pipeline_name
    response['pipeline_id'] = str(uuid.uuid4())
    
    return web.json_response(response)

@director_routes.get('/hello')
async def hello(request):
    return web.Response(text="hello")
    