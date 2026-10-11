"""Authenticated instruction skill library and lifecycle endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.api.v1.models import _redact_config
from app.core.deps import require_user
from app.database import get_db
from app.models.user import User
from app.schemas.skill import SkillCreate, SkillPublishRequest, SkillTestRequest, SkillUpdate
from app.services.skill_service import SkillService

router = APIRouter(prefix="/skills", tags=["skills"])


def require_skill_user(user: User = Depends(require_user)) -> User:
    if not user.is_active:
        raise HTTPException(403, "当前账号已停用")
    return user


@router.get("")
def list_skills(ontology_id: str | None = None, status: str | None = None,
                search: str | None = None, db: Session = Depends(get_db),
                user: User = Depends(require_skill_user)):
    return SkillService(db).list(user, ontology_id, status, search)


@router.get("/catalog")
def skill_catalog(ontology_id: str | None = None, ontology_version_id: str | None = None,
                  db: Session = Depends(get_db), user: User = Depends(require_skill_user)):
    return SkillService(db).catalog(user, ontology_id, ontology_version_id)


@router.post("", status_code=201)
def create_skill(body: SkillCreate, db: Session = Depends(get_db), user: User = Depends(require_skill_user)):
    return SkillService(db).create(body.model_dump(), user)


@router.get("/{skill_id}")
def get_skill(skill_id: str, db: Session = Depends(get_db), user: User = Depends(require_skill_user)):
    service = SkillService(db)
    return service.to_dict(service.get(skill_id, user), user)


@router.put("/{skill_id}")
def update_skill(skill_id: str, body: SkillUpdate, db: Session = Depends(get_db),
                 user: User = Depends(require_skill_user)):
    service = SkillService(db)
    return service.update(service.get(skill_id, user, edit=True), body.model_dump(exclude_unset=True), user)


@router.delete("/{skill_id}", status_code=204)
def delete_skill(skill_id: str, db: Session = Depends(get_db), user: User = Depends(require_skill_user)):
    service = SkillService(db)
    service.delete(service.get(skill_id, user, edit=True))
    return Response(status_code=204)


@router.get("/{skill_id}/versions")
def skill_versions(skill_id: str, db: Session = Depends(get_db), user: User = Depends(require_skill_user)):
    service = SkillService(db)
    return service.versions(service.get(skill_id, user))


@router.get("/{skill_id}/versions/{version}")
def skill_version(skill_id: str, version: int, db: Session = Depends(get_db),
                  user: User = Depends(require_skill_user)):
    service = SkillService(db)
    return service.version_dict(service.version(service.get(skill_id, user), version), include_snapshot=True)


@router.post("/{skill_id}/validate")
def validate_skill(skill_id: str, db: Session = Depends(get_db), user: User = Depends(require_skill_user)):
    service = SkillService(db)
    return _redact_config(service.validate(service.get(skill_id, user), user))


@router.post("/{skill_id}/test")
def test_skill(skill_id: str, request: Request, body: SkillTestRequest | None = None,
               db: Session = Depends(get_db), user: User = Depends(require_skill_user)):
    service = SkillService(db)
    return service.run_tests(service.get(skill_id, user, edit=True), user,
        runner=getattr(request.app.state, "skill_test_runner", None),
        test_case_ids=body.test_case_ids if body else None)


@router.post("/{skill_id}/publish")
def publish_skill(skill_id: str, body: SkillPublishRequest | None = None,
                  db: Session = Depends(get_db), user: User = Depends(require_skill_user)):
    service = SkillService(db)
    return service.publish(service.get(skill_id, user, edit=True), user,
                           description=body.description if body else "")


@router.post("/{skill_id}/archive")
def archive_skill(skill_id: str, db: Session = Depends(get_db), user: User = Depends(require_skill_user)):
    service = SkillService(db)
    return service.archive(service.get(skill_id, user, edit=True), user)


@router.post("/{skill_id}/restore")
def restore_skill(skill_id: str, db: Session = Depends(get_db), user: User = Depends(require_skill_user)):
    service = SkillService(db)
    return service.archive(service.get(skill_id, user, edit=True), user, restore=True)


@router.get("/{skill_id}/references")
def skill_references(skill_id: str, db: Session = Depends(get_db), user: User = Depends(require_skill_user)):
    service = SkillService(db)
    return service.references(service.get(skill_id, user))


@router.get("/{skill_id}/test-runs")
def skill_test_runs(skill_id: str, db: Session = Depends(get_db), user: User = Depends(require_skill_user)):
    service = SkillService(db)
    return service.test_runs(service.get(skill_id, user))
