"""REST API 路由定义，负责将 HTTP 请求转发给语义服务。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from app.services.semantic_service import SemanticService

router = APIRouter(prefix="/api")


def get_service(request: Request) -> SemanticService:
    """从 FastAPI 应用状态中获取单例语义服务。"""
    return request.app.state.semantic_service


@router.get("/summary")
def summary(service: SemanticService = Depends(get_service)) -> dict:
    """返回首页仪表盘所需的汇总数据。"""
    return service.get_summary()


@router.get("/alerts")
def alerts(service: SemanticService = Depends(get_service)) -> list[dict]:
    """返回风险告警列表。"""
    return service.get_alerts()


@router.get("/subscribers")
def search_subscribers(q: str = "", service: SemanticService = Depends(get_service)) -> list[dict]:
    """按关键字检索主实体，支持风险词和标识字段搜索。"""
    return service.search_subscribers(q)


@router.get("/subscribers/{subscriber_id}")
def subscriber_detail(subscriber_id: str, service: SemanticService = Depends(get_service)) -> dict:
    """返回单个实体的详情、证据与局部图谱。"""
    return service.get_subscriber(subscriber_id)


@router.post("/sparql")
async def sparql(request: Request, service: SemanticService = Depends(get_service)) -> dict:
    """执行前端提交的 SPARQL 查询。"""
    payload = await request.body()
    return service.run_sparql(payload.decode("utf-8"))


@router.post("/inference/trigger")
def trigger_inference(service: SemanticService = Depends(get_service)) -> dict:
    """手动触发一次推理并返回统计结果。"""
    return service.run_inference()


@router.post("/upload")
async def upload_data(
    file: UploadFile = File(...),
    service: SemanticService = Depends(get_service),
) -> dict:
    """上传数据文件并按文件类型选择重新初始化或追加解析。"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="filename_required")
    data_dir = service.settings.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    target = data_dir / file.filename
    content = await file.read()
    target.write_bytes(content)
    return service.load_data_file(Path(target))
