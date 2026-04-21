from __future__ import annotations

from app.models.workflow import Workflow, WorkflowExecution
from app.repositories.base import BaseRepository


class WorkflowRepository(BaseRepository[Workflow]):
    model = Workflow

    def list_with_filters(
        self,
        status: str | None = None,
        group: str | None = None,
    ) -> list[Workflow]:
        q = self.db.query(Workflow)
        if status:
            q = q.filter(Workflow.status == status)
        if group:
            q = q.filter(Workflow.group_name == group)
        return q.order_by(Workflow.updated_at.desc()).all()


class WorkflowExecutionRepository(BaseRepository[WorkflowExecution]):
    model = WorkflowExecution

    def list_by_workflow(self, workflow_id: str, limit: int = 50) -> list[WorkflowExecution]:
        return (
            self.db.query(WorkflowExecution)
            .filter(WorkflowExecution.workflow_id == workflow_id)
            .order_by(WorkflowExecution.started_at.desc())
            .limit(limit)
            .all()
        )
