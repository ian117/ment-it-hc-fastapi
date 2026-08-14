from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotificationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    channel: str
    # Datos propios del canal. Su validación NO se hace acá (sería 422 genérico
    # y acoplaría el schema a cada canal): la hace el canal en el despachador,
    # que devuelve 400 antes de escribir en la base.
    payload: dict = Field(default_factory=dict)


class NotificationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = Field(default=None, min_length=1)
    channel: str | None = None
    payload: dict | None = None


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    channel: str
    payload: dict
    status: str
    error_message: str | None
    sent_at: datetime | None
    created_at: datetime


class NotificationPage(BaseModel):
    items: list[NotificationOut]
    page: int
    limit: int
    total: int
