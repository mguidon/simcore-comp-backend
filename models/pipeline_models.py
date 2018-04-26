import networkx as nx
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy_json import MutableJson

Base = declarative_base()

UNKNOWN = 0
PENDING = 1
RUNNING = 2
SUCCESS = 3
FAILED = 4

class ComputationalPipeline(Base):
    __tablename__ = 'comp_pipeline'

    pipeline_id = Column(Integer, primary_key=True)
    dag_adjacency_list = Column(MutableJson)
    state = Column(String, default=UNKNOWN)

    @property
    def execution_graph(self):
        d = self.dag_adjacency_list
        G = nx.DiGraph()

        for node in d.keys():
            nodes = d[node]
            if len(nodes) == 0:
                G.add_node(node)
                continue
            G.add_edges_from([(node, n) for n in nodes])
        return G

    def __repr__(self):
        return '<id {}>'.format(self.id)

class ComputationalTask(Base):
    __tablename__ = 'comp_tasks'
    # this task db id
    task_id = Column(Integer, primary_key=True)
    pipeline_id = Column(Integer, ForeignKey('comp_pipeline.pipeline_id'))
    # dag node id
    node_id = Column(String)
    # celery task id
    job_id = Column(String)

    input = Column(MutableJson)
    output = Column(MutableJson)
    state = Column(Integer, default=UNKNOWN)