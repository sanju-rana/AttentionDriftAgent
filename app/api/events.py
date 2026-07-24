from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.schemas.event import EventCreate

from app.core.dependencies import get_db

from app.database.repositories.event_repository import (
    EventRepository
)

router = APIRouter(
    prefix="/events",
    tags=["Events"]
)


@router.post("")
def create_event(
    payload: EventCreate,
    db: Session = Depends(get_db)
):

    event = EventRepository.create(
        db,
        payload.model_dump()
    )

    return {
        "id": event.id
    }