"""baseline

Revision ID: b5b5e3776f71
Revises: 
Create Date: 2018-05-08 21:28:32.433525

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b5b5e3776f71'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'comp_tasks',
        sa.Column('id', sa.Integer, primary_key=True))


def downgrade():
    op.drop_table('comp_tasks')
