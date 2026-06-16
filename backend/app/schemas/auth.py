from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    token: str
    refresh_token: str
    user: "UserOut"


class UserOut(BaseModel):
    id: str
    username: str
    name: str
    role: str
    permissions: list[str]
    model_config = {"from_attributes": True}


# ── 用户管理 ──

class UserListItem(BaseModel):
    id: str
    username: str
    name: str
    email: str | None = None
    role: str
    is_active: bool = True
    last_login_at: datetime | None = None
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items: list[UserListItem]
    total: int
    page: int
    page_size: int


class UserCreate(BaseModel):
    username: str
    password: str
    name: str
    email: str | None = None
    role: str = "viewer"


class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    role: str | None = None
    is_active: bool | None = None


class ResetPasswordRequest(BaseModel):
    new_password: str


# ── 角色 ──

class RoleOut(BaseModel):
    key: str
    label: str
    description: str
    permissions: list[str]
    user_count: int = 0
    is_system: bool = True


# ── 权限常量 ──

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin": ["entity:read", "entity:write", "entity:delete", "rule:read", "rule:write", "rule:execute", "strategy:read", "strategy:execute", "audit:read", "admin:users"],
    "editor": ["entity:read", "entity:write", "rule:read", "rule:write", "strategy:read", "audit:read"],
    "operator": ["entity:read", "rule:read", "rule:execute", "strategy:read", "strategy:execute", "audit:read"],
    "viewer": ["entity:read", "rule:read", "strategy:read"],
}

ROLE_META: dict[str, dict] = {
    "admin": {"label": "系统管理员", "description": "拥有所有模块的完全管理权限", "is_system": True},
    "editor": {"label": "本体工程师", "description": "负责本体建模和场景开发，拥有读写权限", "is_system": True},
    "operator": {"label": "数据工程师", "description": "负责数据集成和质量治理，拥有执行权限", "is_system": True},
    "viewer": {"label": "只读用户", "description": "仅浏览平台内容，不可修改", "is_system": True},
}

# 功能模块列表（用于权限矩阵展示）
PERMISSION_MODULES = [
    {"key": "entity", "label": "本体中心", "permissions": ["entity:read", "entity:write", "entity:delete"]},
    {"key": "rule", "label": "规则管理", "permissions": ["rule:read", "rule:write", "rule:execute"]},
    {"key": "strategy", "label": "场景中心", "permissions": ["strategy:read", "strategy:execute"]},
    {"key": "audit", "label": "运维审计", "permissions": ["audit:read"]},
    {"key": "admin", "label": "系统管理", "permissions": ["admin:users"]},
]
