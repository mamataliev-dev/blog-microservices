"""empty message

Revision ID: a7eb69287cae
Revises: 
Create Date: 2025-02-19 19:02:56.567726

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a7eb69287cae'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Add the column with NULL allowed
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('password', sa.String(length=255), nullable=True))  # Allow NULL temporarily

    # Step 2: Set a default password for existing users
    op.execute("UPDATE users SET password = 'defaultpassword' WHERE password IS NULL;")

    # Step 3: Now enforce NOT NULL constraint
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('password', nullable=False)  # Enforce NOT NULL


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('password')

    # ### end Alembic commands ###
