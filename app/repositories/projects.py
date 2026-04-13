from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Project


class ProjectRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, *, name: str, description: str | None) -> Project:
        project = Project(name=name, description=description)
        self._session.add(project)
        self._session.flush()
        return project

    def get(self, project_id: int) -> Project | None:
        return self._session.get(Project, project_id)

    def list(self) -> list[Project]:
        statement = select(Project).order_by(Project.id.asc())
        return list(self._session.scalars(statement))
