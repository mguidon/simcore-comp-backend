from model import ComputationalTask, Base

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import exc

engine = create_engine('postgresql://simcore:simcore@localhost:5432/simcoredb')
Session = sessionmaker(bind=engine)

session = Session()

node_id = "1"
task = None
try:
    task = session.query(ComputationalTask).filter_by(node_id=node_id).one()
    task.state = 1
    session.add(task)
    session.commit()
except exc.SQLAlchemyError as err:
    print(err)