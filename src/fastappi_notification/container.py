"""Raíz de composición: único lugar que conoce los canales concretos (ADR-004, ADR-005).

Agregar un canal = su política + su gateway registrados aquí; nada más cambia.
`api/deps.py` solo expone estas fábricas como `Depends()`.
"""

from __future__ import annotations

from functools import cache

from sqlalchemy.orm import Session

from .application.channel_gateway_registry import ChannelGatewayRegistry
from .application.deliver_notification import DeliverNotification
from .application.use_cases.confirm_password_reset import ConfirmPasswordReset
from .application.use_cases.create_notification import CreateNotification
from .application.use_cases.delete_notification import DeleteNotification
from .application.use_cases.get_current_user import GetCurrentUser
from .application.use_cases.get_my_notification import GetMyNotification
from .application.use_cases.list_my_notifications import ListMyNotifications
from .application.use_cases.login import Login
from .application.use_cases.register_user import RegisterUser
from .application.use_cases.request_password_reset import RequestPasswordReset
from .application.use_cases.revise_notification import ReviseNotification
from .core.config import get_settings
from .domain.password_hash import PasswordHash
from .domain.channels import ChannelPolicyRegistry, EmailPolicy, PushPolicy, SmsPolicy
from .infrastructure.channels import (
    SimulatedEmailGateway,
    SimulatedPushGateway,
    SimulatedSmsGateway,
)
from .infrastructure.clock import SystemClock, UuidIdGenerator
from .infrastructure.persistence import (
    SqlAlchemyNotificationRepository,
    SqlAlchemyResetTokenRepository,
    SqlAlchemyUserRepository,
)
from .infrastructure.security import (
    Argon2PasswordHasher,
    JwtTokenIssuer,
    JwtTokenVerifier,
    SecretsResetTokenGenerator,
)

settings = get_settings()

# Piezas sin estado: se crean una vez.
clock = SystemClock()
ids = UuidIdGenerator()
password_hasher = Argon2PasswordHasher()
token_issuer = JwtTokenIssuer(
    settings.jwt_secret, settings.jwt_algorithm, settings.access_token_expire_minutes * 60, clock
)
token_verifier = JwtTokenVerifier(settings.jwt_secret, settings.jwt_algorithm)
reset_token_generator = SecretsResetTokenGenerator()
policies = ChannelPolicyRegistry([EmailPolicy(), SmsPolicy(), PushPolicy()])
gateways = ChannelGatewayRegistry(
    [SimulatedEmailGateway(clock), SimulatedSmsGateway(clock), SimulatedPushGateway(clock)]
)


def user_repository(session: Session) -> SqlAlchemyUserRepository:
    return SqlAlchemyUserRepository(session)


def reset_token_repository(session: Session) -> SqlAlchemyResetTokenRepository:
    return SqlAlchemyResetTokenRepository(session)


def notification_repository(session: Session) -> SqlAlchemyNotificationRepository:
    return SqlAlchemyNotificationRepository(session)


def _deliver(session: Session) -> DeliverNotification:
    return DeliverNotification(notification_repository(session), gateways)


def create_notification(session: Session) -> CreateNotification:
    return CreateNotification(policies, gateways, ids, clock, _deliver(session))


def revise_notification(session: Session) -> ReviseNotification:
    return ReviseNotification(notification_repository(session), policies, clock, _deliver(session))


def list_my_notifications(session: Session) -> ListMyNotifications:
    return ListMyNotifications(notification_repository(session))


def get_my_notification(session: Session) -> GetMyNotification:
    return GetMyNotification(notification_repository(session))


def delete_notification(session: Session) -> DeleteNotification:
    return DeleteNotification(notification_repository(session))


def register_user(session: Session) -> RegisterUser:
    return RegisterUser(user_repository(session), password_hasher, ids, clock)


@cache
def _decoy_hash() -> PasswordHash:
    # Un solo señuelo para todos los `Login` (se crean por request): ADR-013.
    return password_hasher.hash("decoy-password-for-timing-equalization")


def login(session: Session) -> Login:
    return Login(user_repository(session), password_hasher, token_issuer, _decoy_hash())


def get_current_user(session: Session) -> GetCurrentUser:
    return GetCurrentUser(user_repository(session))


def request_password_reset(session: Session) -> RequestPasswordReset:
    return RequestPasswordReset(
        user_repository(session),
        reset_token_repository(session),
        reset_token_generator,
        ids,
        clock,
        settings.reset_token_expire_minutes,
    )


def confirm_password_reset(session: Session) -> ConfirmPasswordReset:
    return ConfirmPasswordReset(
        user_repository(session),
        reset_token_repository(session),
        password_hasher,
        reset_token_generator,
        clock,
    )
