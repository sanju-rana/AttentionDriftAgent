from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.core.dependencies import get_db

from app.database.repositories.event_repository import (
    EventRepository
)

from app.services.analytics.session_analyzer import (
    SessionAnalyzer
)

router = APIRouter(
    prefix="/attention",
    tags=["Attention"]
)


@router.get("/current")
def current_attention(
    db: Session = Depends(get_db)
):

    events = (
        EventRepository
        .get_recent(db)
    )

    analyzer = SessionAnalyzer()

    return analyzer.analyze(events)