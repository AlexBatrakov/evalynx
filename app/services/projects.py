from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Project
from app.repositories.projects import ProjectRepository
from app.schemas.projects import ProjectCreate


class ProjectService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._projects = ProjectRepository(session)

    def create_project(self, payload: ProjectCreate) -> Project:
        project = self._projects.create(
            name=payload.name,
            description=payload.description,
        )
        self._session.commit()
        self._session.refresh(project)
        return project

    def list_projects(self) -> list[Project]:
        return self._projects.list()
