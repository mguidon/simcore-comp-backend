from model import ComputationalTask, Base

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import datetime

engine = create_engine('postgresql://simcore:simcore@localhost:5432/simcoredb')
Session = sessionmaker(bind=engine)


Base.metadata.create_all(engine)

session = Session()

data = {}

data["int"] = 12
data["float"] = 1.0
data["string"] = "test"
data["array"] = [1, 2, 3]

internal_id = 100
for node_id in range(2):
    new_task = ComputationalTask(node_id=node_id, internal_id=internal_id, json_data=data)# submit=datetime.datetime.utcnow())
    internal_id = internal_id + 1
    session.add(new_task)
    session.commit()