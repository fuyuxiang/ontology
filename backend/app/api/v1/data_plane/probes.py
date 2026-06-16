"""/probes — Asset 治理探针 API。"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.data_plane import ProbeRequest, QualityMetricOut
from app.services.data_plane.probe_service import ProbeService

router = APIRouter(prefix="/probes", tags=["data-plane:probes"])


def _run(db: Session, kind: str, body: ProbeRequest) -> QualityMetricOut:
    try:
        m = ProbeService(db).run(body.asset_id, kind, column=body.column,
                                  threshold=body.threshold)
        return m
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/row_count", response_model=QualityMetricOut)
def probe_row_count(body: ProbeRequest, db: Session = Depends(get_db)):
    return _run(db, "row_count", body)


@router.post("/freshness", response_model=QualityMetricOut)
def probe_freshness(body: ProbeRequest, db: Session = Depends(get_db)):
    return _run(db, "freshness", body)


@router.post("/null_ratio", response_model=QualityMetricOut)
def probe_null_ratio(body: ProbeRequest, db: Session = Depends(get_db)):
    return _run(db, "null_ratio", body)


@router.post("/distinct_count", response_model=QualityMetricOut)
def probe_distinct_count(body: ProbeRequest, db: Session = Depends(get_db)):
    return _run(db, "distinct_count", body)


@router.post("/pk_uniqueness", response_model=QualityMetricOut)
def probe_pk_uniqueness(body: ProbeRequest, db: Session = Depends(get_db)):
    return _run(db, "pk_uniqueness", body)


@router.post("/schema_drift", response_model=QualityMetricOut)
def probe_schema_drift(body: ProbeRequest, db: Session = Depends(get_db)):
    return _run(db, "schema_drift", body)


@router.get("/asset/{asset_id}", response_model=list[QualityMetricOut])
def list_for_asset(
    asset_id: str,
    kind: str | None = None,
    column: str | None = None,
    since: datetime | None = None,
    db: Session = Depends(get_db),
):
    return ProbeService(db).history(asset_id, kind=kind, column=column, limit=500)
