from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

UNKNOWN = 0
PENDING = 1
RUNNING = 2
SUCCESS = 3
FAILED = 4

class ComputationalTask(Base):
    __tablename__ = 'comp_tasks'
    # this task db id
    task_id = Column(Integer, primary_key=True)
    # dag node id
    node_id = Column(Integer)
    # celery task id
    job_id = Column(String)
    # internal id (better for debugging, nodes from 1 to N)
    internal_id = Column(Integer)

    state = Column(Integer, default=UNKNOWN)

    json_data = Column(JSON)
#
#    submit = Column(DateTime)
#    start = Column(DateTime)
#    end = Column(DateTime)