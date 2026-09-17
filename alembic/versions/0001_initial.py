"""initial v2 schema

Revision ID: 0001
Revises:
Create Date: 2026-09-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "system_config",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("host_name_enc", sa.String, nullable=False),
        sa.Column("domain_name_enc", sa.String, nullable=False),
        sa.Column("api_open_minutes", sa.Integer, nullable=False, server_default="5"),
        sa.Column("api_lockout_minutes", sa.Integer, nullable=False, server_default="60"),
        sa.Column("schema_version", sa.String, nullable=False),
    )

    op.create_table(
        "user_accounts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username_enc", sa.String, nullable=False),
        sa.Column("username_index", sa.String, nullable=False, unique=True),
        sa.Column("otp_seed_enc", sa.String, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("active_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("date_added", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_user_accounts_username_index", "user_accounts", ["username_index"])

    op.create_table(
        "app_servers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("server_name_enc", sa.String, nullable=False),
        sa.Column("server_name_index", sa.String, nullable=False),
        sa.Column("ip_address_enc", sa.String, nullable=False),
        sa.Column("ip_address_index", sa.String, nullable=False),
        sa.Column("server_salt_enc", sa.String, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("date_added", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("active_until", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_app_servers_server_name_index", "app_servers", ["server_name_index"])
    op.create_index("ix_app_servers_ip_address_index", "app_servers", ["ip_address_index"])

    op.create_table(
        "secrets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("secret_name_index", sa.String, nullable=False, unique=True),
        sa.Column("secret_value_enc", sa.String, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_secrets_secret_name_index", "secrets", ["secret_name_index"])

    op.create_table(
        "secret_acl",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("server_id", sa.Integer, sa.ForeignKey("app_servers.id"), nullable=False),
        sa.Column("secret_id", sa.Integer, sa.ForeignKey("secrets.id"), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "pending_enrollments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("system_id_index", sa.String, nullable=False),
        sa.Column("payload_enc", sa.String, nullable=False),
        sa.Column("date_requested", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("enrollment_attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("enrollment_complete", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("is_expired", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_pending_enrollments_system_id_index", "pending_enrollments", ["system_id_index"])

    op.create_table(
        "event_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("event_type", sa.String, nullable=False),
        sa.Column("significant", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("details", sa.String, nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("event_log")
    op.drop_table("pending_enrollments")
    op.drop_table("secret_acl")
    op.drop_table("secrets")
    op.drop_table("app_servers")
    op.drop_table("user_accounts")
    op.drop_table("system_config")
