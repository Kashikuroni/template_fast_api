"""Initial revision

Revision ID: b07b22043b82
Revises: 
Create Date: 2025-08-20 15:57:34.902126

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b07b22043b82'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE SCHEMA IF NOT EXISTS auth")
    # op.execute("CREATE TYPE auth.system_roles AS ENUM ('owner', 'superuser', 'free_user', 'paid_user', 'guest')")
    # op.execute("CREATE TYPE auth.workspaces_roles AS ENUM ('owner', 'member', 'guest')")
    op.create_table('user',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('email', sa.String(length=128), nullable=False),
    sa.Column('first_name', sa.String(length=48), nullable=False),
    sa.Column('last_name', sa.String(length=48), nullable=False),
    sa.Column('username', sa.String(length=48), nullable=True),
    sa.Column('is_superuser', sa.Boolean(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('hashed_password', sa.String(length=1024), nullable=False, comment='Password hash (bcrypt/argon2)'),
    sa.Column('role', postgresql.ENUM('OWNER', 'SUPERUSER', 'FREE_USER', 'PAID_USER', 'GUEST', name='system_roles', schema='auth'), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False, comment='Время создания записи'),
    sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False, comment='Время последнего обновления'),
    sa.PrimaryKeyConstraint('id'),
    schema='auth'
    )
    op.create_table('workspace',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=64), nullable=False),
    sa.Column('description', sa.String(length=512), nullable=False),
    sa.Column('owner_id', sa.UUID(), nullable=False, comment='Владелец аккаунта'),
    sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False, comment='Время создания записи'),
    sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False, comment='Время последнего обновления'),
    sa.ForeignKeyConstraint(['owner_id'], ['auth.user.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id'),
    schema='auth'
    )
    op.create_table('workspace_user',
    sa.Column('workspace_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('role', postgresql.ENUM('OWNER', 'MEMBER', 'GUEST', name='workspaces_roles', schema='auth'), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False, comment='Время создания записи'),
    sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False, comment='Время последнего обновления'),
    sa.ForeignKeyConstraint(['user_id'], ['auth.user.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['workspace_id'], ['auth.workspace.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('workspace_id', 'user_id'),
    schema='auth'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('workspace_user', schema='auth')
    op.drop_table('workspace', schema='auth')
    op.drop_table('user', schema='auth')
