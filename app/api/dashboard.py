from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db

from app.database.repositories.event_repository import (
    EventRepository
)

from app.services.analytics.dashboard_service import (
    DashboardService
)

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


@router.get("/metrics")
def metrics(
    interval_minutes: int = Query(
        5,
        ge=1,
        le=120,
        description="Bucket size in minutes for the attention trend line"
    ),
    db: Session = Depends(get_db)
):

    events = (
        EventRepository.get_recent(
            db,
            limit=1000
        )
    )

    return (
        DashboardService
        .build_dashboard(events, interval_minutes=interval_minutes)
    )