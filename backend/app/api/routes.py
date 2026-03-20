from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from app.services.semantic_service import SemanticService

router = APIRouter(prefix="/api")


def get_service(request: Request) -> SemanticService:
    return request.app.state.semantic_service


@router.get("/summary")
def summary(service: SemanticService = Depends(get_service)) -> dict:
    return service.get_summary()


@router.get("/alerts")
def alerts(service: SemanticService = Depends(get_service)) -> list[dict]:
    return service.get_alerts()


@router.get("/subscribers")
def search_subscribers(q: str = "", service: SemanticService = Depends(get_service)) -> list[dict]:
    return service.search_subscribers(q)


@router.get("/subscribers/{subscriber_id}")
def subscriber_detail(subscriber_id: str, service: SemanticService = Depends(get_service)) -> dict:
    return service.get_subscriber(subscriber_id)


@router.post("/sparql")
async def sparql(request: Request, service: SemanticService = Depends(get_service)) -> dict:
    payload = await request.body()
    return service.run_sparql(payload.decode("utf-8"))


@router.post("/inference/trigger")
def trigger_inference(service: SemanticService = Depends(get_service)) -> dict:
    return service.run_inference()


@router.post("/upload")
async def upload_data(
    file: UploadFile = File(...),
    service: SemanticService = Depends(get_service),
) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="filename_required")
    data_dir = service.settings.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    target = data_dir / file.filename
    content = await file.read()
    target.write_bytes(content)
    return service.load_data_file(Path(target))

