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

comp_backend_routes = web.RouteTableDef()

async def async_request(method, session, url, json=None, timeout=10):
    async with async_timeout.timeout(timeout):
        if method == "GET":
            async with session.get(url) as response:
                return await response.json()
        elif method == "POST":
            async with session.post(url, json=json) as response:
                return await response.json()

@comp_backend_routes.get('/start_pipeline')
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

    #  ccreate some fake data for now
    data = {}
    data['pipeline_name'] = "My Pipeline"
    node_ids = []
    for i in range(8):
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

    url = "http://director:8010/start_pipeline"
   
    
    response = None
    async with aiohttp.ClientSession() as session:
        response = await async_request(method='POST', session=session, url=url, json=data)

    return web.Response(text="Pipeline started, director returns {}".format(str(response)))
