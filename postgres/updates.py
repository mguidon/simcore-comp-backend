from model import ComputationalTask, Base

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.attributes import flag_modified

import datetime

engine = create_engine('postgresql://simcore:simcore@localhost:5432/simcoredb')
Session = sessionmaker(bind=engine)


Base.metadata.create_all(engine)

session = Session()

tasks = session.query(ComputationalTask).all()
for task in tasks:
    data = task.json_data
    data["string"] = data["string"] + "@"
    flag_modified(task, "json_data")
    session.commit()