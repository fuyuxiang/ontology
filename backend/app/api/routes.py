"""
模块功能：
- REST API 路由定义，负责将 HTTP 请求转发给语义服务。
- 该文件位于 `backend/app/api/routes.py`，定义 FastAPI 路由、请求模型和依赖注入入口，把 HTTP 请求转发到语义服务与平台上下文。
- 文件中定义的核心类包括：`ActionExecutionRequest`, `AgentAskRequest`, `ScenarioActivationRequest`。
- 文件中对外暴露或复用的主要函数包括：`_raise_agent_http_error`, `get_context`, `get_service`, `get_agent`, `platform_summary`, `platform_scenarios`, `activate_scenario`, `summary`, `alerts`, `search_subscribers`, `subscriber_detail`, `sparql`, `ask_agent`, `trigger_inference`, `cases`, `case_detail`, `tasks`, `execute_action`, `upload_data`。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from app.agent import SupervisorAgentService
from app.platform import PlatformContext
from app.services.semantic_service import SemanticService

router = APIRouter(prefix="/api")


class ActionExecutionRequest(BaseModel):
    """
    功能：
    - 动作执行请求。
    - 该类定义在 `backend/app/api/routes.py` 中，用于组织与 `ActionExecutionRequest` 相关的数据或行为。
    - 类中声明的主要字段包括：`actionId`, `caseId`, `entityId`, `actorRole`, `actorId`, `actorAreaId`, `parameters`。
    """

    actionId: str
    caseId: str | None = None
    entityId: str | None = None
    actorRole: str = "ops_manager"
    actorId: str = "api-user"
    actorAreaId: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class AgentAskRequest(BaseModel):
    """
    功能：
    - 监督 agent 查询请求。
    - 该类定义在 `backend/app/api/routes.py` 中，用于组织与 `AgentAskRequest` 相关的数据或行为。
    - 类中声明的主要字段包括：`question`, `actorRole`, `actorId`, `actorAreaId`。
    """

    question: str
    actorRole: str = "ops_manager"
    actorId: str = "agent-console"
    actorAreaId: str | None = None


class ScenarioActivationRequest(BaseModel):
    """
    功能：
    - 场景激活请求。
    - 该类定义在 `backend/app/api/routes.py` 中，用于组织与 `ScenarioActivationRequest` 相关的数据或行为。
    - 类中声明的主要字段包括：`scenarioKey`。
    """

    scenarioKey: str


def _raise_agent_http_error(exc: ValueError) -> None:
    """
    功能：
    - 将监督式 agent 的内部错误映射为更清晰的 HTTP 响应。

    输入：
    - `exc`: 函数执行所需的 `exc` 参数。

    输出：
    - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
    """
    detail = str(exc)
    if detail == "llm_not_configured":
        raise HTTPException(status_code=503, detail="智能问答模型未配置") from exc
    if detail == "llm_timeout":
        raise HTTPException(status_code=504, detail="智能问答模型响应超时，请稍后重试") from exc
    if detail.startswith("llm_network_error:"):
        raise HTTPException(status_code=502, detail="智能问答模型网络异常，请稍后重试") from exc
    if detail.startswith("llm_http_error:"):
        raise HTTPException(status_code=502, detail="智能问答模型服务异常，请稍后重试") from exc
    if detail.startswith("llm_"):
        raise HTTPException(status_code=502, detail="智能问答模型返回异常响应") from exc
    raise HTTPException(status_code=400, detail=detail) from exc


def get_context(request: Request) -> PlatformContext:
    """
    功能：
    - 获取平台上下文。

    输入：
    - `request`: 当前 HTTP 请求对象。

    输出：
    - 返回值: 返回 `PlatformContext` 类型结果，供后续流程继续消费。
    """
    return request.app.state.platform_context


def get_service(request: Request) -> SemanticService:
    """
    功能：
    - 从 FastAPI 应用状态中获取单例语义服务。

    输入：
    - `request`: 当前 HTTP 请求对象。

    输出：
    - 返回值: 返回 `SemanticService` 类型结果，供后续流程继续消费。
    """
    return get_context(request).service()


def get_agent(request: Request) -> SupervisorAgentService:
    """
    功能：
    - 从 FastAPI 应用状态中获取监督 agent。

    输入：
    - `request`: 当前 HTTP 请求对象。

    输出：
    - 返回值: 返回 `SupervisorAgentService` 类型结果，供后续流程继续消费。
    """
    return get_context(request).agent()


@router.get("/platform")
def platform_summary(context: PlatformContext = Depends(get_context)) -> dict:
    """
    功能：
    - 返回平台层概览。

    输入：
    - `context`: 错误提示或日志中使用的上下文说明。

    输出：
    - 返回值: 返回字典结构，包含本次处理产生的结果数据。
    """
    return context.platform_summary()


@router.get("/platform/scenarios")
def platform_scenarios(context: PlatformContext = Depends(get_context)) -> list[dict]:
    """
    功能：
    - 返回可用场景包列表。

    输入：
    - `context`: 错误提示或日志中使用的上下文说明。

    输出：
    - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
    """
    return context.list_scenarios()


@router.post("/platform/scenarios/activate")
def activate_scenario(payload: ScenarioActivationRequest, context: PlatformContext = Depends(get_context)) -> dict:
    """
    功能：
    - 激活指定场景包。

    输入：
    - `payload`: 请求体或内部处理中使用的载荷数据。
    - `context`: 错误提示或日志中使用的上下文说明。

    输出：
    - 返回值: 返回字典结构，包含本次处理产生的结果数据。
    """
    try:
        return context.activate_scenario(payload.scenarioKey)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/summary")
def summary(service: SemanticService = Depends(get_service)) -> dict:
    """
    功能：
    - 返回首页仪表盘所需的汇总数据。

    输入：
    - `service`: 语义服务实例。

    输出：
    - 返回值: 返回字典结构，包含本次处理产生的结果数据。
    """
    return service.get_summary()


@router.get("/alerts")
def alerts(service: SemanticService = Depends(get_service)) -> list[dict]:
    """
    功能：
    - 返回风险告警列表。

    输入：
    - `service`: 语义服务实例。

    输出：
    - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
    """
    return service.get_alerts()


@router.get("/subscribers")
def search_subscribers(q: str = "", service: SemanticService = Depends(get_service)) -> list[dict]:
    """
    功能：
    - 按关键字检索主实体，支持风险词和标识字段搜索。

    输入：
    - `q`: 函数执行所需的 `q` 参数。
    - `service`: 语义服务实例。

    输出：
    - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
    """
    return service.search_subscribers(q)


@router.get("/subscribers/{subscriber_id}")
def subscriber_detail(subscriber_id: str, service: SemanticService = Depends(get_service)) -> dict:
    """
    功能：
    - 返回单个实体的详情、证据与局部图谱。

    输入：
    - `subscriber_id`: 函数执行所需的 `subscriber_id` 参数。
    - `service`: 语义服务实例。

    输出：
    - 返回值: 返回字典结构，包含本次处理产生的结果数据。
    """
    return service.get_subscriber(subscriber_id)


@router.post("/sparql")
async def sparql(request: Request, service: SemanticService = Depends(get_service)) -> dict:
    """
    功能：
    - 执行前端提交的 SPARQL 查询。

    输入：
    - `request`: 当前 HTTP 请求对象。
    - `service`: 语义服务实例。

    输出：
    - 返回值: 返回字典结构，包含本次处理产生的结果数据。
    """
    payload = await request.body()
    return service.run_sparql(payload.decode("utf-8"))


@router.post("/agent/ask")
def ask_agent(payload: AgentAskRequest, agent: SupervisorAgentService = Depends(get_agent)) -> dict:
    """
    功能：
    - 通过监督 agent 进行 ontology-aware 问答。

    输入：
    - `payload`: 请求体或内部处理中使用的载荷数据。
    - `agent`: 监督式 agent 服务实例。

    输出：
    - 返回值: 返回字典结构，包含本次处理产生的结果数据。
    """
    try:
        return agent.ask(
            payload.question,
            actor_role=payload.actorRole,
            actor_id=payload.actorId,
            actor_area_id=payload.actorAreaId,
        )
    except ValueError as exc:
        _raise_agent_http_error(exc)


@router.post("/inference/trigger")
def trigger_inference(service: SemanticService = Depends(get_service)) -> dict:
    """
    功能：
    - 手动触发一次推理并返回统计结果。

    输入：
    - `service`: 语义服务实例。

    输出：
    - 返回值: 返回字典结构，包含本次处理产生的结果数据。
    """
    return service.run_inference()


@router.get("/cases")
def cases(service: SemanticService = Depends(get_service)) -> list[dict]:
    """
    功能：
    - 返回运营 case 列表。

    输入：
    - `service`: 语义服务实例。

    输出：
    - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
    """
    return service.list_cases()


@router.get("/cases/{case_id}")
def case_detail(case_id: str, service: SemanticService = Depends(get_service)) -> dict:
    """
    功能：
    - 返回单个运营 case 详情。

    输入：
    - `case_id`: 运营 case 标识。
    - `service`: 语义服务实例。

    输出：
    - 返回值: 返回字典结构，包含本次处理产生的结果数据。
    """
    return service.get_case(case_id)


@router.get("/tasks")
def tasks(
    status: str | None = None,
    assignee_role: str | None = None,
    service: SemanticService = Depends(get_service),
) -> list[dict]:
    """
    功能：
    - 按状态或角色筛选任务列表。

    输入：
    - `status`: 筛选或设置时使用的状态值。
    - `assignee_role`: 任务或 case 负责人角色标识。
    - `service`: 语义服务实例。

    输出：
    - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
    """
    return service.list_tasks(status=status, assignee_role=assignee_role)


@router.post("/actions/execute")
def execute_action(payload: ActionExecutionRequest, service: SemanticService = Depends(get_service)) -> dict:
    """
    功能：
    - 执行运营动作。

    输入：
    - `payload`: 请求体或内部处理中使用的载荷数据。
    - `service`: 语义服务实例。

    输出：
    - 返回值: 返回字典结构，包含本次处理产生的结果数据。
    """
    try:
        return service.execute_action(
            action_id=payload.actionId,
            actor_role=payload.actorRole,
            actor_id=payload.actorId,
            actor_area_id=payload.actorAreaId,
            entity_id=payload.entityId,
            case_id=payload.caseId,
            parameters=payload.parameters,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/upload")
async def upload_data(
    file: UploadFile = File(...),
    service: SemanticService = Depends(get_service),
) -> dict:
    """
    功能：
    - 上传数据文件并按文件类型选择重新初始化或追加解析。

    输入：
    - `file`: 函数执行所需的 `file` 参数。
    - `service`: 语义服务实例。

    输出：
    - 返回值: 返回字典结构，包含本次处理产生的结果数据。
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="filename_required")
    data_dir = service.settings.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    target = data_dir / file.filename
    content = await file.read()
    target.write_bytes(content)
    return service.load_data_file(Path(target))
