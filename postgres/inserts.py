from model import ComputationalTask, Base

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import datetime

engine = create_engine('postgresql://simcore:simcore@localhost:5432/simcoredb')
Session = sessionmaker(bind=engine)


Base.metadata.create_all(engine)

session = Session()

internal_id = 100
for node_id in range(20):
    new_task = ComputationalTask(node_id=node_id, internal_id=internal_id)# submit=datetime.datetime.utcnow())
    internal_id = internal_id + 1
    session.add(new_task)
    session.commit()