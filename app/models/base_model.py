from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PhoneRequest(BaseModel):
    phone: str


class CodeRequest(BaseModel):
    profile_id: int
    code: str


class PasswordRequest(BaseModel):
    profile_id: int
    password: str


class MessagesRequest(BaseModel):
    profile_id: int
    limit: int = 50


class SendMessageRequest(BaseModel):
    profile_id: int
    text: str
    tg_receiver: str


class DialogsRequest(BaseModel):
    profile_id: int
    limit: int = 50


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    id: int
    email: str
    created_at: str
    api_calls_today: int
