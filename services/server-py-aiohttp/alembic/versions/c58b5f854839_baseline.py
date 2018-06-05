"""baseline

Revision ID: c58b5f854839
Revises: 
Create Date: 2018-05-11 07:31:11.458369

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c58b5f854839'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('comp_pipeline',
        sa.Column('pipeline_id', sa.Integer, primary_key=True))

def downgrade():
    op.drop_table('comp_pipeline')
