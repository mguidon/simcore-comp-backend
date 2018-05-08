from model import ComputationalTask, Base

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import exc, and_

engine = create_engine('postgresql://simcore:simcore@localhost:5432/simcoredb')
Session = sessionmaker(bind=engine)

session = Session()

node_id = "1"
task = None
try:
    task = session.query(ComputationalTask).filter(and_(ComputationalTask.node_id==node_id, ComputationalTask.job_id==None)).one()
    task.state = 1
    print(str(task.job_id))
    session.add(task)
    session.commit()
except exc.SQLAlchemyError as err:
    print(err)