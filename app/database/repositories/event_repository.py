from sqlalchemy.orm import Session

from app.database.models.event import Event


class EventRepository:

    @staticmethod
    def create(
        db: Session,
        payload: dict
    ):

        event = Event(**payload)

        db.add(event)

        db.commit()

        db.refresh(event)

        return event

    @staticmethod
    def get_recent(
        db: Session,
        limit: int = 100
    ):

        return (
            db.query(Event)
            .order_by(Event.id.desc())
            .limit(limit)
            .all()
        )