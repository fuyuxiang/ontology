"""本体→数据资产映射 API"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import ontology_mapping_service

router = APIRouter(prefix="/doc-builder", tags=["doc-builder"])


class MappingRequest(BaseModel):
    session_id: str
    ontology: dict


@router.post("/mapping")
async def mapping(req: MappingRequest, db: Session = Depends(get_db)):
    return StreamingResponse(
        ontology_mapping_service.map_ontology_stream(req.ontology, db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
