from __future__ import annotations

from sqlmodel import Session, select

from packages.infrastructure.db.models.provider import Provider


class ProviderRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_slug(self, *, slug: str) -> Provider | None:
        stmt = select(Provider).where(Provider.slug == slug)
        return self.session.exec(stmt).first()

    def list_active(self) -> list[Provider]:
        stmt = (
            select(Provider)
            .where(Provider.is_active.is_(True))
            .order_by(Provider.id)
        )
        return list(self.session.exec(stmt).all())

    def ensure_provider(
        self,
        *,
        slug: str,
        display_name: str | None = None,
        api_base_url: str | None = None,
    ) -> Provider:
        existing = self.get_by_slug(slug=slug)
        resolved_display = (
            display_name
            if display_name is not None
            else slug.replace("-", " ").title()[:128]
        )
        if existing is None:
            row = Provider(
                slug=slug,
                display_name=resolved_display,
                api_base_url=api_base_url,
                is_active=True,
            )
            self.session.add(row)
            self.session.flush()
            return row
        if display_name is not None:
            existing.display_name = display_name[:128]
        if api_base_url is not None:
            existing.api_base_url = api_base_url
        self.session.add(existing)
        self.session.flush()
        return existing

