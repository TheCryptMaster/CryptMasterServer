from pydantic import BaseModel


class StartAuthRequest(BaseModel):
    system_id: str


class StartAuthResponse(BaseModel):
    response: str
    nonce: str | None = None


class EnableApiRequest(BaseModel):
    user_name: str
    user_pass: str
    otp: str


class EnableApiResponse(BaseModel):
    response: str
    active_until: str | None = None


class EnrollServerRequest(BaseModel):
    system_id: str
    system_salt: str


class GetSecretRequest(BaseModel):
    system_id: str
    auth_response: str | None = None
    requested_password: str


class GetSecretResponse(BaseModel):
    response: str
    secret: str | None = None
