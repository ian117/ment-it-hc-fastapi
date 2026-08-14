from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from ...core.db import get_db
from ...models import User
from ...schemas.notification import (
    NotificationCreate,
    NotificationOut,
    NotificationPage,
    NotificationUpdate,
)
from ...services import notifications as service
from ..deps import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("", response_model=NotificationOut, status_code=status.HTTP_201_CREATED)
def create_notification(
    data: NotificationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.create_and_send(db, user, data)


@router.get("", response_model=NotificationPage)
def list_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=service.MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    items, total = service.list_owned(db, user, page, limit)
    return NotificationPage(items=items, page=page, limit=limit, total=total)


@router.get("/{notification_id}", response_model=NotificationOut)
def get_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.get_owned(db, user, notification_id)


@router.patch("/{notification_id}", response_model=NotificationOut)
def update_notification(
    notification_id: int,
    data: NotificationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.update(db, user, notification_id, data)


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service.delete(db, user, notification_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
