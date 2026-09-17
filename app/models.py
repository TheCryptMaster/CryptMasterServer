"""SQLAlchemy 2.0 ORM models.

Sensitive columns store the ":"-joined salt:nonce:ciphertext token produced by
app.crypto.encrypt_field / app.password_crypto.encrypt_with_password. Columns
that need to be looked up by value (username, server_name, ip_address) also
carry a `*_index` blind-index column (app.crypto.blind_index) so lookups use
an indexed equality match instead of decrypting every row or, as in v1,
string-formatting the plaintext straight into SQL.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class SystemConfig(Base):
    __tablename__ = "system_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    host_name_enc: Mapped[str] = mapped_column(String, nullable=False)
    domain_name_enc: Mapped[str] = mapped_column(String, nullable=False)
    api_open_minutes: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    api_lockout_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    schema_version: Mapped[str] = mapped_column(String, nullable=False)


class User(Base):
    __tablename__ = "user_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username_enc: Mapped[str] = mapped_column(String, nullable=False)
    username_index: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    otp_seed_enc: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    active_until: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    date_added: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AppServer(Base):
    __tablename__ = "app_servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    server_name_enc: Mapped[str] = mapped_column(String, nullable=False)
    server_name_index: Mapped[str] = mapped_column(String, nullable=False, index=True)
    ip_address_enc: Mapped[str] = mapped_column(String, nullable=False)
    ip_address_index: Mapped[str] = mapped_column(String, nullable=False, index=True)
    server_salt_enc: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    date_added: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    active_until: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    acl_entries: Mapped[list["SecretAcl"]] = relationship(back_populates="server")


class Secret(Base):
    __tablename__ = "secrets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    secret_name_index: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    secret_value_enc: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    acl_entries: Mapped[list["SecretAcl"]] = relationship(back_populates="secret")


class SecretAcl(Base):
    """Explicit allow-list of which app server may fetch which secret.

    v1 defined this table but never enforced it -- provide_secret() would
    hand back any secret to any authenticated server. It's enforced in
    app/auth.py:get_secret_for_server now.
    """

    __tablename__ = "secret_acl"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("app_servers.id"), nullable=False)
    secret_id: Mapped[int] = mapped_column(ForeignKey("secrets.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    server: Mapped[AppServer] = relationship(back_populates="acl_entries")
    secret: Mapped[Secret] = relationship(back_populates="acl_entries")


class PendingEnrollment(Base):
    __tablename__ = "pending_enrollments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_id_index: Mapped[str] = mapped_column(String, nullable=False, index=True)
    payload_enc: Mapped[str] = mapped_column(String, nullable=False)
    date_requested: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    enrollment_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enrollment_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_expired: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class EventLog(Base):
    __tablename__ = "event_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    significant: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    details: Mapped[str] = mapped_column(String, nullable=False)
    event_timestamp: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
