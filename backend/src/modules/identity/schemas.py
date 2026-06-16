"""Pydantic schemas for identity endpoints."""
from pydantic import BaseModel

from src.modules.identity.models import UserRoleEnum


class RegisterRequest(BaseModel):
    username: str = ""
    email: str = ""
    password: str = ""
    name: str = ""
    role: UserRoleEnum = UserRoleEnum.athlete


class LoginRequest(BaseModel):
    identifier: str = ""
    password: str = ""


class ForgotPasswordRequest(BaseModel):
    email: str = ""


class ResetPasswordRequest(BaseModel):
    token: str = ""
    new_password: str = ""


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    preferred_distance_unit: str | None = None
