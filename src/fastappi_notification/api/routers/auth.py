from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from ...application.use_cases.confirm_password_reset import ConfirmPasswordReset
from ...application.use_cases.get_current_user import GetCurrentUser
from ...application.use_cases.login import Login
from ...application.use_cases.register_user import RegisterUser
from ...application.use_cases.request_password_reset import RequestPasswordReset
from ...core.config import get_settings
from ...core.limiter import limiter
from .. import deps
from ..openapi import problem_responses
from ..schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetRequestedResponse,
    RegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])

RESET_REQUESTED_MESSAGE = "If the email exists, a reset link was sent"
PASSWORD_UPDATED_MESSAGE = "Password updated"


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses=problem_responses(400, 409),
)
def register(
    body: RegisterRequest,
    use_case: RegisterUser = Depends(deps.register_user_use_case),
) -> UserResponse:
    user = use_case.execute(email=body.email, password=body.password)
    return UserResponse.from_domain(user)


@router.post(
    "/login",
    response_model=AccessTokenResponse,
    responses=problem_responses(400, 401, 429),
)
@limiter.limit(get_settings().login_rate_limit)
def login(
    request: Request,  # requerido por slowapi
    body: LoginRequest,
    use_case: Login = Depends(deps.login_use_case),
) -> AccessTokenResponse:
    issued = use_case.execute(email=body.email, password=body.password)
    return AccessTokenResponse(
        access_token=issued.access_token, token_type="Bearer", expires_in=issued.expires_in
    )


@router.get("/me", response_model=UserResponse, responses=problem_responses(401))
def me(
    user_id: UUID = Depends(deps.current_user_id),
    use_case: GetCurrentUser = Depends(deps.get_current_user_use_case),
) -> UserResponse:
    return UserResponse.from_domain(use_case.execute(user_id=user_id))


@router.post(
    "/password-reset/request",
    response_model=PasswordResetRequestedResponse,
    response_model_exclude_unset=True,
    status_code=status.HTTP_202_ACCEPTED,
    responses=problem_responses(400, 429),
)
@limiter.limit(get_settings().reset_request_rate_limit)
def request_password_reset(
    request: Request,  # requerido por slowapi
    body: PasswordResetRequest,
    expose_reset_token: bool = Depends(deps.expose_reset_token),
    use_case: RequestPasswordReset = Depends(deps.request_password_reset_use_case),
) -> PasswordResetRequestedResponse:
    """Idéntica exista o no el email; `resetToken` solo si existe y no es producción.

    El token en claro nunca se escribe en el log (ADR-014).
    """
    token = use_case.execute(email=body.email)
    if token is not None and expose_reset_token:
        return PasswordResetRequestedResponse(message=RESET_REQUESTED_MESSAGE, reset_token=token)
    return PasswordResetRequestedResponse(message=RESET_REQUESTED_MESSAGE)


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
    responses=problem_responses(400),
)
def confirm_password_reset(
    body: PasswordResetConfirm,
    use_case: ConfirmPasswordReset = Depends(deps.confirm_password_reset_use_case),
) -> MessageResponse:
    use_case.execute(token=body.token, new_password=body.new_password)
    return MessageResponse(message=PASSWORD_UPDATED_MESSAGE)
