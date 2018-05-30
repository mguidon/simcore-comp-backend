import uuid 
import json
from pprint import pprint
import datetime
import pytest

import models
from models.pipeline_models import ComputationalPipeline, ComputationalTask

import os 
__DIR_PATH__ = os.path.dirname(os.path.realpath(__file__))

def _find_entry_point(G):
    result = []
    for node in G.nodes:
        if len(list(G.predecessors(node))) == 0:
            result.append(node)
    return result

def _check_for_link_and_process(port):
    print(port)
    _port = port['value']
    print("__", _port)
    if _port and isinstance(_port, str):
        if _port.startswith('link.'):
            link = _port.split('.')
            print(link)
            object_name = os.path.join(link[1], link[2])
            input_name = port['key']
            print(input_name, object_name)
            return True
    return False

def test_pipeline_generation():
    mockfile_path = os.path.join(__DIR_PATH__, 'mockup.json')
    with open(mockfile_path) as f:
        mockup = json.load(f)

    assert mockup
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
        print(type(task['input']))
        
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

    pipeline_id = pipeline.pipeline_id
    pipeline_name = "mockup"
    internal_id = 1

    comp_tasks = []
    for node_id in tasks:
        task = tasks[node_id]
        new_task = ComputationalTask(pipeline_id=pipeline_id, node_id=node_id, internal_id=internal_id, image=task['image'],
                    input=task['input'], output=task['output'], submit=datetime.datetime.utcnow())
        comp_tasks.append(new_task)
        internal_id = internal_id+1
        
        for port in task['input']:
            _check_for_link_and_process(port)



    graph = pipeline.execution_graph
    next_node = _find_entry_point(graph)
    for n in next_node:
        print(n)
  

  
    assert 0



