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
    phone: str
    code: str


class PasswordRequest(BaseModel):
    phone: str
    password: str


class MessagesRequest(BaseModel):
    profile_username: str
    limit: int = 50


class SendMessageRequest(BaseModel):
    profile_username: str
    text: str
    tg_receiver: str


class DialogsRequest(BaseModel):
    profile_username: str
    limit: int = 50
