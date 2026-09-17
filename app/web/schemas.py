from pydantic import BaseModel, Field


# --- auth / setup ---


class SetupStatus(BaseModel):
    initialized: bool


class CreateDatabaseRequest(BaseModel):
    host_name: str
    domain_name: str


class DefaultAdminInfo(BaseModel):
    username: str
    password: str
    note: str


class LoginRequest(BaseModel):
    username: str
    password: str
    otp: str | None = None


class LoginResponse(BaseModel):
    must_change_password: bool
    role: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    current_otp: str | None = None
    new_password: str = Field(min_length=12)


class ChangePasswordResponse(BaseModel):
    provisioning_uri: str


class ConfirmOtpRequest(BaseModel):
    otp: str


class WhoAmIResponse(BaseModel):
    role: str
    must_change_password: bool


# --- servers ---


class CreateServerRequest(BaseModel):
    system_id: str
    server_salt: str
    label: str = ""
    ip_addresses: list[str] = Field(default_factory=list)


class AddServerIpRequest(BaseModel):
    ip_address: str


class ServerOut(BaseModel):
    id: int
    system_id: str
    label: str
    is_active: bool
    active_until: str
    ip_addresses: list[str]


class PendingEnrollmentOut(BaseModel):
    id: int
    system_id: str
    ip_address: str
    requested_at: str
    attempts: int


# --- users ---


class CreateUserRequest(BaseModel):
    email: str
    role: str
    active_days: int = 365


class CreateUserResponse(BaseModel):
    provisioning_uri: str
    temporary_password: str


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    must_change_password: bool
    active_until: str


class ResetOtpRequest(BaseModel):
    new_password: str = Field(min_length=12)


class ResetOtpResponse(BaseModel):
    provisioning_uri: str


# --- secrets ---


class CreateSecretRequest(BaseModel):
    name: str
    value: str


class SecretOut(BaseModel):
    id: int
    name: str
    is_active: bool
    server_ids_with_access: list[int]


class GrantAccessRequest(BaseModel):
    server_id: int
    secret_id: int


# --- logs ---


class LogEntryOut(BaseModel):
    id: int
    event_type: str
    significant: bool
    details: str
    timestamp: str


# --- backup ---


class BackupExportRequest(BaseModel):
    """Step-up auth for a high-value action: re-supply password + a fresh
    OTP code, even though the caller already has a valid session."""

    password: str
    otp: str


class BackupExportResponse(BaseModel):
    data: dict


class BackupRestoreRequest(BaseModel):
    data: dict


# --- legacy (v1) migration, third first-run option ---


class MigrateLegacyServerEntry(BaseModel):
    system_id: str
    ip_address: str


class MigrateLegacyUserEntry(BaseModel):
    email: str
    password: str


class MigrateLegacyRequest(BaseModel):
    old_dsn: str
    old_entropy: str
    secrets: list[str] = Field(default_factory=list)
    app_servers: list[MigrateLegacyServerEntry] = Field(default_factory=list)
    users: list[MigrateLegacyUserEntry] = Field(default_factory=list)
    dry_run: bool = False


class MigrateLegacyResponse(BaseModel):
    secrets_migrated: int
    app_servers_migrated: int
    users_migrated: int
    skipped: int
    failed: int
    log: list[str]
