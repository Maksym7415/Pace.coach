"""Pydantic schemas for identity endpoints."""
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str = ""
    password: str = ""
    name: str = ""


class LoginRequest(BaseModel):
    email: str = ""
    password: str = ""


class ForgotPasswordRequest(BaseModel):
    email: str = ""


class ResetPasswordRequest(BaseModel):
    token: str = ""
    new_password: str = ""


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    avatar_url: str | None = None
    preferred_distance_unit: str | None = None
