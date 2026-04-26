from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    token: str
    user: "UserOut"


class UserOut(BaseModel):
    id: str
    username: str
    name: str
    role: str
    permissions: list[str]
    model_config = {"from_attributes": True}


ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin": ["entity:read", "entity:write", "entity:delete", "rule:read", "rule:write", "rule:execute", "strategy:read", "strategy:execute", "audit:read", "admin:users"],
    "editor": ["entity:read", "entity:write", "rule:read", "rule:write", "strategy:read", "audit:read"],
    "operator": ["entity:read", "rule:read", "rule:execute", "strategy:read", "strategy:execute", "audit:read"],
    "viewer": ["entity:read", "rule:read", "strategy:read"],
}
