"""web UI support: user roles, multi-IP server allow-lists

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_accounts",
        sa.Column("role", sa.String, nullable=False, server_default="operator"),
    )
    op.add_column(
        "user_accounts",
        sa.Column("must_change_password", sa.Boolean, nullable=False, server_default=sa.false()),
    )

    op.add_column(
        "app_servers",
        sa.Column("label", sa.String, nullable=False, server_default=""),
    )

    # secrets.secret_name was previously stored only as a one-way blind index
    # (secret_name_index), matching v1's behavior -- but that makes it
    # impossible to list secrets by name in the admin UI or export them by
    # name in a backup. Add a reversible, master-key-encrypted copy. Existing
    # rows from schema 0001 get an empty placeholder; re-set each one's name
    # via the admin UI (or `cli.manage`) after upgrading.
    op.add_column(
        "secrets",
        sa.Column("secret_name_enc", sa.String, nullable=False, server_default=""),
    )

    op.create_table(
        "app_server_ips",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("server_id", sa.Integer, sa.ForeignKey("app_servers.id"), nullable=False),
        sa.Column("ip_address_enc", sa.String, nullable=False),
        sa.Column("ip_address_index", sa.String, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_app_server_ips_ip_address_index", "app_server_ips", ["ip_address_index"])

    # Existing single-IP-per-server data can't be carried forward automatically:
    # ip_address_index was a blind index of the IP, not the IP itself, and the
    # matching ip_address_enc token used context "ip_address" -- decryptable,
    # but only from within the app (this migration has no access to the master
    # key). Operators upgrading from schema 0001 should re-add each server's
    # IP(s) via the admin UI or `cli.manage` after this migration runs; the
    # column is dropped rather than silently left stale.
    op.drop_index("ix_app_servers_ip_address_index", table_name="app_servers")
    op.drop_column("app_servers", "ip_address_index")
    op.drop_column("app_servers", "ip_address_enc")


def downgrade() -> None:
    op.add_column("app_servers", sa.Column("ip_address_enc", sa.String, nullable=True))
    op.add_column("app_servers", sa.Column("ip_address_index", sa.String, nullable=True))
    op.create_index("ix_app_servers_ip_address_index", "app_servers", ["ip_address_index"])
    op.drop_index("ix_app_server_ips_ip_address_index", table_name="app_server_ips")
    op.drop_table("app_server_ips")
    op.drop_column("secrets", "secret_name_enc")
    op.drop_column("app_servers", "label")
    op.drop_column("user_accounts", "must_change_password")
    op.drop_column("user_accounts", "role")
