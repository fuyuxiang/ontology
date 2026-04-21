from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
import httpx

from app.database import get_db
from app.models.agent import ModelRegistry

router = APIRouter(prefix="/models", tags=["models"])


class ModelCreate(BaseModel):
    name: str
    provider: str
    model_name: str
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    capabilities: Optional[list] = None
    config_json: Optional[dict] = None


class ModelUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    model_name: Optional[str] = None
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    capabilities: Optional[list] = None
    config_json: Optional[dict] = None
    status: Optional[str] = None


def _model_out(m: ModelRegistry) -> dict:
    return {
        "id": m.id,
        "name": m.name,
        "provider": m.provider,
        "model_name": m.model_name,
        "api_base": m.api_base,
        "api_key": "***" if m.api_key else None,
        "capabilities": m.capabilities or [],
        "config_json": m.config_json or {},
        "status": m.status,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


@router.get("")
def list_models(db: Session = Depends(get_db)):
    return [_model_out(m) for m in db.query(ModelRegistry).all()]


@router.post("", status_code=201)
def create_model(body: ModelCreate, db: Session = Depends(get_db)):
    m = ModelRegistry(**body.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return _model_out(m)


@router.get("/{mid}")
def get_model(mid: str, db: Session = Depends(get_db)):
    m = db.get(ModelRegistry, mid)
    if not m:
        raise HTTPException(404, "Model not found")
    return _model_out(m)


@router.put("/{mid}")
def update_model(mid: str, body: ModelUpdate, db: Session = Depends(get_db)):
    m = db.get(ModelRegistry, mid)
    if not m:
        raise HTTPException(404, "Model not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return _model_out(m)


@router.delete("/{mid}")
def delete_model(mid: str, db: Session = Depends(get_db)):
    m = db.get(ModelRegistry, mid)
    if not m:
        raise HTTPException(404, "Model not found")
    db.delete(m)
    db.commit()
    return {"ok": True}


@router.post("/{mid}/test")
def test_model(mid: str, db: Session = Depends(get_db)):
    m = db.get(ModelRegistry, mid)
    if not m:
        raise HTTPException(404, "Model not found")
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=m.api_key or "sk-placeholder",
            base_url=m.api_base or "https://api.openai.com/v1",
        )
        cfg = m.config_json or {}
        resp = client.chat.completions.create(
            model=m.model_name,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=cfg.get("max_tokens", 10),
            temperature=cfg.get("temperature", 0.1),
        )
        return {"ok": True, "reply": resp.choices[0].message.content}
    except Exception as e:
        return {"ok": False, "error": str(e)}
