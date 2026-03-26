from __future__ import annotations

from sqlmodel import Session, select

from packages.infrastructure.db.models.provider import Provider


class ProviderRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_slug(self, *, slug: str) -> Provider | None:
        stmt = select(Provider).where(Provider.slug == slug)
        return self.session.exec(stmt).first()

