from __future__ import annotations

from datetime import datetime
from app.models.scene import (
    AipScene, AipSceneVersion, AipSceneExecution, AipSceneTrigger,
)
from app.repositories.base import BaseRepository


class AipSceneRepository(BaseRepository[AipScene]):
    model = AipScene

    def list_with_filters(
        self,
        status: str | None = None,
        group: str | None = None,
        keyword: str | None = None,
    ) -> list[AipScene]:
        q = self.db.query(AipScene)
        if status:
            q = q.filter(AipScene.status == status)
        if group:
            q = q.filter(AipScene.group_name == group)
        if keyword:
            kw = f"%{keyword}%"
            q = q.filter((AipScene.name.like(kw)) | (AipScene.description.like(kw)))
        return q.order_by(AipScene.updated_at.desc()).all()


class AipSceneVersionRepository(BaseRepository[AipSceneVersion]):
    model = AipSceneVersion

    def list_by_scene(self, scene_id: str, limit: int = 100) -> list[AipSceneVersion]:
        return (
            self.db.query(AipSceneVersion)
            .filter(AipSceneVersion.scene_id == scene_id)
            .order_by(AipSceneVersion.version.desc())
            .limit(limit)
            .all()
        )


class AipSceneExecutionRepository(BaseRepository[AipSceneExecution]):
    model = AipSceneExecution

    def list_by_scene(
        self,
        scene_id: str | None = None,
        status: str | None = None,
        triggered_by: str | None = None,
        limit: int = 100,
    ) -> list[AipSceneExecution]:
        q = self.db.query(AipSceneExecution)
        if scene_id:
            q = q.filter(AipSceneExecution.scene_id == scene_id)
        if status:
            q = q.filter(AipSceneExecution.status == status)
        if triggered_by:
            q = q.filter(AipSceneExecution.triggered_by == triggered_by)
        return q.order_by(AipSceneExecution.started_at.desc()).limit(limit).all()


class AipSceneTriggerRepository(BaseRepository[AipSceneTrigger]):
    model = AipSceneTrigger

    def get_by_scene(self, scene_id: str) -> AipSceneTrigger | None:
        return (
            self.db.query(AipSceneTrigger)
            .filter(AipSceneTrigger.scene_id == scene_id)
            .first()
        )

    def get_by_webhook_path(self, path: str) -> AipSceneTrigger | None:
        return (
            self.db.query(AipSceneTrigger)
            .filter(AipSceneTrigger.webhook_path == path)
            .first()
        )

    def list_enabled(self, type_: str | None = None) -> list[AipSceneTrigger]:
        q = self.db.query(AipSceneTrigger).filter(AipSceneTrigger.enabled == True)  # noqa: E712
        if type_:
            q = q.filter(AipSceneTrigger.type == type_)
        return q.all()

    def mark_fired(self, trigger: AipSceneTrigger) -> None:
        trigger.last_fired_at = datetime.utcnow()
        trigger.fire_count = (trigger.fire_count or 0) + 1
