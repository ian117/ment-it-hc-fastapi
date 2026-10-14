from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from ...application.use_cases.create_notification import CreateNotification
from ...application.use_cases.delete_notification import DeleteNotification
from ...application.use_cases.get_my_notification import GetMyNotification
from ...application.use_cases.list_my_notifications import ListMyNotifications
from ...application.use_cases.revise_notification import ReviseNotification
from ...models import User
from .. import deps
from ..schemas.notification import (
    CreateNotificationRequest,
    NotificationPage,
    NotificationResponse,
    ReviseNotificationRequest,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
def create_notification(
    body: CreateNotificationRequest,
    user: User = Depends(deps.get_current_user),
    use_case: CreateNotification = Depends(deps.create_notification_use_case),
) -> NotificationResponse:
    notification = use_case.execute(
        owner_id=user.id,
        title=body.title,
        content=body.content,
        channel=body.channel,
        recipient=body.payload.recipient,
    )
    return NotificationResponse.from_domain(notification)


@router.get("", response_model=NotificationPage)
def list_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(deps.get_current_user),
    use_case: ListMyNotifications = Depends(deps.list_my_notifications_use_case),
) -> NotificationPage:
    return NotificationPage.from_result(use_case.execute(user.id, page, limit))


@router.get("/{id}", response_model=NotificationResponse)
def get_notification(
    user: User = Depends(deps.get_current_user),
    id: UUID = Depends(deps.notification_id),
    use_case: GetMyNotification = Depends(deps.get_my_notification_use_case),
) -> NotificationResponse:
    return NotificationResponse.from_domain(use_case.execute(user.id, id))


@router.patch("/{id}", response_model=NotificationResponse)
def revise_notification(
    body: ReviseNotificationRequest,
    user: User = Depends(deps.get_current_user),
    id: UUID = Depends(deps.notification_id),
    use_case: ReviseNotification = Depends(deps.revise_notification_use_case),
) -> NotificationResponse:
    notification = use_case.execute(
        user.id,
        id,
        title=body.title,
        content=body.content,
        recipient=body.payload.recipient if body.payload is not None else None,
    )
    return NotificationResponse.from_domain(notification)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_notification(
    user: User = Depends(deps.get_current_user),
    id: UUID = Depends(deps.notification_id),
    use_case: DeleteNotification = Depends(deps.delete_notification_use_case),
) -> Response:
    use_case.execute(user.id, id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
