"""add basic comp_tasks columns

Revision ID: 5d63e4a9c008
Revises: b5b5e3776f71
Create Date: 2018-05-08 21:33:17.204635

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5d63e4a9c008'
down_revision = 'b5b5e3776f71'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('comp_tasks', sa.Column('internal_id', sa.Integer(), nullable=True))
    op.add_column('comp_tasks', sa.Column('job_id', sa.String(), nullable=True))
    op.add_column('comp_tasks', sa.Column('node_id', sa.Integer(), nullable=True))
    op.add_column('comp_tasks', sa.Column('state', sa.Integer(), nullable=True))
    op.add_column('comp_tasks', sa.Column('task_id', sa.Integer(), nullable=False))
    op.drop_column('comp_tasks', 'id')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('comp_tasks', sa.Column('id', sa.INTEGER(), nullable=False))
    op.drop_column('comp_tasks', 'task_id')
    op.drop_column('comp_tasks', 'state')
    op.drop_column('comp_tasks', 'node_id')
    op.drop_column('comp_tasks', 'job_id')
    op.drop_column('comp_tasks', 'internal_id')
    # ### end Alembic commands ###