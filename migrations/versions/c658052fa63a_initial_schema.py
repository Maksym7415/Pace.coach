"""initial_schema

Revision ID: c658052fa63a
Revises:
Create Date: 2026-02-28 00:05:05.373494

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c658052fa63a'
down_revision = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('avatar_url', sa.String(512), nullable=True),
        sa.Column('expo_push_token', sa.String(512), nullable=True),
        sa.Column('password_reset_token', sa.String(255), nullable=True),
        sa.Column('password_reset_expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_password_reset_token'), 'users', ['password_reset_token'], unique=False)

    op.create_table(
        'users_strava',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('strava_athlete_id', sa.BigInteger(), nullable=False),
        sa.Column('access_token', sa.String(255), nullable=False),
        sa.Column('refresh_token', sa.String(255), nullable=False),
        sa.Column('token_expires_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_users_strava_strava_athlete_id'), 'users_strava', ['strava_athlete_id'], unique=False)

    op.create_table(
        'shoes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('activity_type', sa.String(64), nullable=False),
        sa.Column('brand', sa.String(128), nullable=False),
        sa.Column('model', sa.String(128), nullable=False),
        sa.Column('nick', sa.String(128), nullable=True),
        sa.Column('max_distance_km', sa.Float(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_shoes_user_id'), 'shoes', ['user_id'], unique=False)

    op.create_table(
        'activities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('total_distance_km', sa.Float(), nullable=False),
        sa.Column('source', sa.String(32), nullable=False),
        sa.Column('strava_activity_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_activities_strava_activity_id'), 'activities', ['strava_activity_id'], unique=False)
    op.create_index(op.f('ix_activities_user_id'), 'activities', ['user_id'], unique=False)

    op.create_table(
        'activity_shoes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('activity_id', sa.Integer(), nullable=False),
        sa.Column('shoe_id', sa.Integer(), nullable=False),
        sa.Column('distance_km', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['activity_id'], ['activities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['shoe_id'], ['shoes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_activity_shoes_activity_id'), 'activity_shoes', ['activity_id'], unique=False)
    op.create_index(op.f('ix_activity_shoes_shoe_id'), 'activity_shoes', ['shoe_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_activity_shoes_shoe_id'), table_name='activity_shoes')
    op.drop_index(op.f('ix_activity_shoes_activity_id'), table_name='activity_shoes')
    op.drop_table('activity_shoes')
    op.drop_index(op.f('ix_activities_user_id'), table_name='activities')
    op.drop_index(op.f('ix_activities_strava_activity_id'), table_name='activities')
    op.drop_table('activities')
    op.drop_index(op.f('ix_shoes_user_id'), table_name='shoes')
    op.drop_table('shoes')
    op.drop_index(op.f('ix_users_strava_strava_athlete_id'), table_name='users_strava')
    op.drop_table('users_strava')
    op.drop_index(op.f('ix_users_password_reset_token'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
