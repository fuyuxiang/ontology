from pydantic import BaseModel


class ResourceMetrics(BaseModel):
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float


class ServiceStatus(BaseModel):
    name: str
    status: str
    response_ms: float | None = None


class ResponseHistoryPoint(BaseModel):
    service_name: str
    response_ms: float | None
    status: str
    collected_at: str


class AlertItem(BaseModel):
    id: int
    level: str
    service_name: str
    message: str
    resolved: bool
    created_at: str
    resolved_at: str | None = None


class LLMStatsResponse(BaseModel):
    total_24h: int
    by_module: dict[str, dict]


class OntologyStatsResponse(BaseModel):
    total_entities: int
    by_type: dict[str, int]


class AgentActivityResponse(BaseModel):
    total_agents: int
    published_agents: int
    total_skills: int


class DashboardOverview(BaseModel):
    resources: ResourceMetrics
    services: list[ServiceStatus]
    alerts: list[AlertItem]
    llm_stats: LLMStatsResponse
    ontology_stats: OntologyStatsResponse
    agent_activity: AgentActivityResponse
