import asyncio
import logging
import random
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models.datasource import DataSource
from app.models.pipeline import Pipeline, PipelineRun

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipelines", tags=["pipelines"])


# ============= Schemas =============

class PipelineCreate(BaseModel):
    name: str
    description: str = ""
    source: str = ""
    target: str = ""
    datasource_id: str | None = None
    steps: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    schedule: str = ""
    step_duration_ms: int = 1500


class PipelineUpdate(PipelineCreate):
    pass


class PipelineRunOut(BaseModel):
    id: str
    pipeline_id: str
    status: str
    step_index: int
    step_label: str
    records: int
    duration_ms: int
    progress: int
    started_at: str

    @classmethod
    def from_orm_obj(cls, r: PipelineRun) -> "PipelineRunOut":
        return cls(
            id=r.id, pipeline_id=r.pipeline_id, status=r.status,
            step_index=r.step_index, step_label=r.step_label or "",
            records=r.records or 0, duration_ms=r.duration_ms or 0,
            progress=r.progress or 0,
            started_at=r.started_at.isoformat() if r.started_at else "",
        )
# __APPEND_HERE__


class PipelineOut(BaseModel):
    id: str
    name: str
    description: str
    source: str
    target: str
    datasource_id: str | None
    steps: list[str]
    tags: list[str]
    schedule: str
    step_duration_ms: int
    status: str
    last_run_at: str | None
    last_records: int | None
    last_objects: int | None
    last_duration_ms: int | None
    recent_runs: list[PipelineRunOut] = Field(default_factory=list)

    @classmethod
    def from_orm_obj(cls, p: Pipeline, recent_runs: list[PipelineRun] | None = None) -> "PipelineOut":
        return cls(
            id=p.id, name=p.name, description=p.description or "",
            source=p.source or "", target=p.target or "",
            datasource_id=p.datasource_id,
            steps=list(p.steps or []), tags=list(p.tags or []),
            schedule=p.schedule or "",
            step_duration_ms=p.step_duration_ms or 1500,
            status=p.status or "idle",
            last_run_at=p.last_run_at.isoformat() if p.last_run_at else None,
            last_records=p.last_records, last_objects=p.last_objects,
            last_duration_ms=p.last_duration_ms,
            recent_runs=[PipelineRunOut.from_orm_obj(r) for r in (recent_runs or [])],
        )


class SummaryOut(BaseModel):
    total: int
    running: int
    success: int
    stopped: int
    error: int
    idle: int
    total_records_last_run: int


class PipelineListOut(BaseModel):
    items: list[PipelineOut]
    summary: SummaryOut


class RunListOut(BaseModel):
    items: list[PipelineRunOut]


# ============= Helpers =============

def _validate_payload(p: PipelineCreate) -> None:
    if not p.name.strip():
        raise HTTPException(400, "请输入管线名称")
    if not p.steps:
        raise HTTPException(400, "至少需要一个步骤")
    if p.step_duration_ms < 100 or p.step_duration_ms > 60000:
        raise HTTPException(400, "单步耗时范围 100~60000")


def _summary(items: list[Pipeline]) -> SummaryOut:
    s = SummaryOut(total=len(items), running=0, success=0, stopped=0, error=0, idle=0, total_records_last_run=0)
    for p in items:
        st = p.status or "idle"
        if st == "running":
            s.running += 1
        elif st == "success":
            s.success += 1
        elif st == "stopped":
            s.stopped += 1
        elif st == "error":
            s.error += 1
        else:
            s.idle += 1
        if p.last_records:
            s.total_records_last_run += p.last_records
    return s


def _recent_runs(db: Session, pipeline_id: str, limit: int = 10) -> list[PipelineRun]:
    return (
        db.query(PipelineRun)
        .filter(PipelineRun.pipeline_id == pipeline_id)
        .order_by(PipelineRun.started_at.desc())
        .limit(limit)
        .all()
    )


def _seed_if_empty(db: Session) -> None:
    if db.query(Pipeline).count() > 0:
        return
    from app.utils.identifiers import gen_uuid

    presets = [
        {
            "name": "客户主数据接入",
            "description": "从 B 域数仓抽取客户主数据，落入 Customer 本体对象",
            "source": "B域数仓 · DWA_V_D_CUS_CB_USER_INFO",
            "target": "Customer 对象",
            "steps": ["抽取", "清洗", "主键解析", "本体映射"],
            "tags": ["核心", "日更"],
            "schedule": "0 2 * * *",
            "last_records": 40929,
            "last_objects": 40929,
            "last_duration_ms": 6800,
            "status": "success",
        },
        {
            "name": "合约数据接入",
            "description": "同步合约表，构建 Contract 实例",
            "source": "CBSS · DWA_V_D_CUS_CB_ACT_INFO",
            "target": "Contract 对象",
            "steps": ["抽取", "过期标记", "本体映射"],
            "tags": ["日更"],
            "schedule": "0 3 * * *",
            "last_records": 40929, "last_objects": 40929, "last_duration_ms": 4900,
            "status": "success",
        },
        {
            "name": "工单数据接入",
            "description": "客服工单全量接入",
            "source": "客服工单系统 · DWD_D_EVT_KF_ORDER_MAIN",
            "target": "WorkOrder 对象",
            "steps": ["抽取", "工单去重", "本体映射"],
            "tags": [],
            "schedule": "*/30 * * * *",
            "last_records": 82757, "last_objects": 82757, "last_duration_ms": 12300,
            "status": "idle",
        },
        {
            "name": "携转预警结果回写",
            "description": "将携转风险评分写入 t_mnp_risk_warning",
            "source": "风险评分模型",
            "target": "t_mnp_risk_warning",
            "steps": ["模型推理", "阈值过滤", "结果落库"],
            "tags": ["MNP"],
            "schedule": "",
            "last_records": 1284, "last_objects": 1284, "last_duration_ms": 5400,
            "status": "idle",
        },
    ]
    now = datetime.utcnow()
    for p in presets:
        db.add(Pipeline(id=gen_uuid(), step_duration_ms=1500, last_run_at=now, **p))
    db.commit()
# __APPEND_2__


# ============= Background worker =============

_worker_task: asyncio.Task | None = None


def _mock_records(p: Pipeline, db: Session) -> int:
    if p.datasource_id:
        ds = db.query(DataSource).filter(DataSource.id == p.datasource_id).first()
        if ds and ds.record_count:
            return int(ds.record_count)
    if p.last_records:
        jitter = int((random.random() - 0.5) * max(100, p.last_records * 0.05))
        return max(0, p.last_records + jitter)
    return 1000 + random.randint(0, 100000)


def _advance_runs_once() -> None:
    db = SessionLocal()
    try:
        runs = db.query(PipelineRun).filter(PipelineRun.status == "running").all()
        for run in runs:
            p = db.query(Pipeline).filter(Pipeline.id == run.pipeline_id).first()
            if not p:
                run.status = "stopped"
                run.finished_at = datetime.utcnow()
                continue
            steps = list(p.steps or [])
            step_count = max(1, len(steps))
            step_dur = p.step_duration_ms or 1500
            total_dur = step_count * step_dur
            elapsed = int((datetime.utcnow() - run.started_at).total_seconds() * 1000)
            progress = min(100, int(elapsed / total_dur * 100))
            step_idx = min(step_count - 1, elapsed // step_dur)
            run.progress = progress
            run.step_index = int(step_idx)
            run.step_label = steps[step_idx] if steps else ""
            if elapsed >= total_dur:
                records = _mock_records(p, db)
                run.status = "success"
                run.step_index = step_count - 1
                run.step_label = steps[-1] if steps else ""
                run.records = records
                run.duration_ms = total_dur
                run.progress = 100
                run.finished_at = datetime.utcnow()
                p.status = "success"
                p.last_run_at = run.finished_at
                p.last_records = records
                p.last_objects = records
                p.last_duration_ms = total_dur
        db.commit()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"pipeline worker tick failed: {e}")
        db.rollback()
    finally:
        db.close()


async def _worker_loop() -> None:
    while True:
        try:
            await asyncio.to_thread(_advance_runs_once)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"pipeline worker loop error: {e}")
        await asyncio.sleep(0.8)


def start_worker() -> None:
    global _worker_task
    if _worker_task and not _worker_task.done():
        return
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        return
    _worker_task = loop.create_task(_worker_loop())


# ============= Routes =============

@router.get("", response_model=PipelineListOut)
def list_pipelines(
    keyword: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    _seed_if_empty(db)
    q = db.query(Pipeline)
    if status:
        q = q.filter(Pipeline.status == status)
    items = q.order_by(Pipeline.updated_at.desc()).all()
    if keyword:
        kw = keyword.lower().strip()
        items = [
            p for p in items
            if any(kw in (s or "").lower() for s in [p.name, p.description, p.source, p.target])
        ]
    return PipelineListOut(
        items=[PipelineOut.from_orm_obj(p) for p in items],
        summary=_summary(items),
    )


@router.get("/runs/active", response_model=RunListOut)
def list_active_runs(db: Session = Depends(get_db)):
    runs = db.query(PipelineRun).filter(PipelineRun.status == "running").all()
    return RunListOut(items=[PipelineRunOut.from_orm_obj(r) for r in runs])


@router.get("/{pipeline_id}", response_model=PipelineOut)
def get_pipeline(pipeline_id: str, db: Session = Depends(get_db)):
    p = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not p:
        raise HTTPException(404, "管线不存在")
    return PipelineOut.from_orm_obj(p, _recent_runs(db, p.id))
# __APPEND_3__


@router.post("", response_model=PipelineOut, status_code=201)
def create_pipeline(body: PipelineCreate, db: Session = Depends(get_db)):
    _validate_payload(body)
    p = Pipeline(
        name=body.name.strip(),
        description=body.description,
        source=body.source,
        target=body.target,
        datasource_id=body.datasource_id or None,
        steps=body.steps,
        tags=body.tags,
        schedule=body.schedule,
        step_duration_ms=body.step_duration_ms,
        status="idle",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return PipelineOut.from_orm_obj(p)


@router.put("/{pipeline_id}", response_model=PipelineOut)
def update_pipeline(pipeline_id: str, body: PipelineUpdate, db: Session = Depends(get_db)):
    _validate_payload(body)
    p = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not p:
        raise HTTPException(404, "管线不存在")
    if p.status == "running":
        raise HTTPException(400, "管线运行中，无法编辑")
    p.name = body.name.strip()
    p.description = body.description
    p.source = body.source
    p.target = body.target
    p.datasource_id = body.datasource_id or None
    p.steps = body.steps
    p.tags = body.tags
    p.schedule = body.schedule
    p.step_duration_ms = body.step_duration_ms
    db.commit()
    db.refresh(p)
    return PipelineOut.from_orm_obj(p, _recent_runs(db, p.id))


@router.delete("/{pipeline_id}", status_code=204)
def delete_pipeline(pipeline_id: str, db: Session = Depends(get_db)):
    p = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not p:
        raise HTTPException(404, "管线不存在")
    db.query(PipelineRun).filter(PipelineRun.pipeline_id == pipeline_id).delete()
    db.delete(p)
    db.commit()


@router.post("/{pipeline_id}/run", response_model=PipelineRunOut)
def run_pipeline(pipeline_id: str, db: Session = Depends(get_db)):
    p = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not p:
        raise HTTPException(404, "管线不存在")
    existing = (
        db.query(PipelineRun)
        .filter(PipelineRun.pipeline_id == pipeline_id, PipelineRun.status == "running")
        .first()
    )
    if existing:
        return PipelineRunOut.from_orm_obj(existing)
    if not p.steps:
        raise HTTPException(400, "管线没有步骤")
    run = PipelineRun(
        pipeline_id=pipeline_id,
        status="running",
        step_index=0,
        step_label=p.steps[0] if p.steps else "",
        records=0,
        duration_ms=0,
        progress=0,
        started_at=datetime.utcnow(),
    )
    p.status = "running"
    db.add(run)
    db.commit()
    db.refresh(run)
    return PipelineRunOut.from_orm_obj(run)


@router.post("/{pipeline_id}/stop", response_model=PipelineRunOut)
def stop_pipeline(pipeline_id: str, db: Session = Depends(get_db)):
    p = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not p:
        raise HTTPException(404, "管线不存在")
    run = (
        db.query(PipelineRun)
        .filter(PipelineRun.pipeline_id == pipeline_id, PipelineRun.status == "running")
        .order_by(PipelineRun.started_at.desc())
        .first()
    )
    if not run:
        raise HTTPException(400, "管线未在运行")
    run.status = "stopped"
    run.finished_at = datetime.utcnow()
    p.status = "stopped"
    db.commit()
    db.refresh(run)
    return PipelineRunOut.from_orm_obj(run)



