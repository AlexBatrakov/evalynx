from __future__ import annotations

from fastapi import APIRouter, status

from app.api.dependencies import ProjectServiceDep
from app.schemas.projects import ProjectCreate, ProjectRead

router = APIRouter(tags=["projects"])


@router.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    service: ProjectServiceDep,
) -> ProjectRead:
    return ProjectRead.model_validate(service.create_project(payload))


@router.get("/projects", response_model=list[ProjectRead])
def list_projects(service: ProjectServiceDep) -> list[ProjectRead]:
    return [ProjectRead.model_validate(project) for project in service.list_projects()]
