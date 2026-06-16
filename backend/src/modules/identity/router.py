"""Identity API routes."""
import logging

from fastapi import APIRouter, Depends, Request

from src.core.auth import CurrentUser
from src.core.rate_limit import (
    FORGOT_PASSWORD_MAX_PER_WINDOW,
    FORGOT_PASSWORD_WINDOW_SEC,
    LOGIN_MAX_PER_WINDOW,
    LOGIN_WINDOW_SEC,
    REGISTER_MAX_PER_WINDOW,
    REGISTER_WINDOW_SEC,
    is_rate_limited,
)
from src.core.responses import error_json, success_json
from src.modules.identity.deps import get_identity_service
from src.modules.identity.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
)
from src.modules.identity.service import IdentityService

logger = logging.getLogger("coach_app.identity")
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _auth_rate_key(endpoint: str, request: Request) -> str:
    client = request.client.host if request.client else "unknown"
    return f"{endpoint}:{client}"


@router.post("/register")
def register(
    body: RegisterRequest,
    request: Request,
    service: IdentityService = Depends(get_identity_service),
):
    if is_rate_limited(_auth_rate_key("register", request), REGISTER_MAX_PER_WINDOW, REGISTER_WINDOW_SEC):
        logger.warning("Register rate limit exceeded for %s", request.client)
        raise error_json(429, "Too many requests. Try again later.")
    result, err, status = service.register(
        body.username, body.email, body.password, body.name, body.role
    )
    if err:
        raise error_json(status, err)
    return success_json(result, status_code=status)


@router.post("/login")
def login(
    body: LoginRequest,
    request: Request,
    service: IdentityService = Depends(get_identity_service),
):
    if is_rate_limited(_auth_rate_key("login", request), LOGIN_MAX_PER_WINDOW, LOGIN_WINDOW_SEC):
        logger.warning("Login rate limit exceeded for %s", request.client)
        raise error_json(429, "Too many requests. Try again later.")
    result, err, status = service.login(body.identifier, body.password)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.post("/forgot-password")
def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    service: IdentityService = Depends(get_identity_service),
):
    if is_rate_limited(
        _auth_rate_key("forgot-password", request),
        FORGOT_PASSWORD_MAX_PER_WINDOW,
        FORGOT_PASSWORD_WINDOW_SEC,
    ):
        logger.warning("Forgot-password rate limit exceeded for %s", request.client)
        return success_json({"message": "If the email exists, a reset link was sent"})
    result, err, status = service.forgot_password(body.email)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, service: IdentityService = Depends(get_identity_service)):
    result, err, status = service.reset_password(body.token, body.new_password)
    if err:
        raise error_json(status, err)
    return success_json(result)


@router.get("/me")
def me(user: CurrentUser, service: IdentityService = Depends(get_identity_service)):
    return success_json(service.get_me(user))


@router.put("/profile")
def update_profile(
    body: UpdateProfileRequest,
    user: CurrentUser,
    service: IdentityService = Depends(get_identity_service),
):
    return success_json(service.update_profile(user, body.model_dump(exclude_unset=True)))
