from model import ComputationalTask, Base

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import exc, and_

engine = create_engine('postgresql://simcore:simcore@localhost:5432/simcoredb')
Session = sessionmaker(bind=engine)

session = Session()

tasks = session.query(ComputationalTask).all()
for task in tasks:
    data = task.json_data
    print(type(data))
    for key in data.keys():
        print("key: {}, value: {}".format(key, data[key]))