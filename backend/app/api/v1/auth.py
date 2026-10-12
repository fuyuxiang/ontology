from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.deps import require_admin, require_user
from app.core.permissions import role_permissions
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    decode_token_payload,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    PERMISSION_MODULES,
    ROLE_META,
    ROLE_PERMISSIONS,
    LoginRequest,
    ResetPasswordRequest,
    RoleOut,
    TokenResponse,
    UserCreate,
    UserListItem,
    UserListResponse,
    UserOut,
    UserUpdate,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/platform-config")
def platform_config(db: Session = Depends(get_db)):
    """Public presentation settings for login and the shell; never return secrets."""
    from app.api.v1.system_config import _get_config_value
    defaults = {"system_name": "本体管理平台", "language": "zh-CN", "timezone": "Asia/Shanghai"}
    return {key: _get_config_value(db, f"basic.{key}") or fallback for key, fallback in defaults.items()}


def validate_password(db: Session, password: str) -> None:
    from app.api.v1.system_config import _get_config_value
    minimum = int(_get_config_value(db, "auth.password_min_length") or "8")
    rules = set((_get_config_value(db, "auth.password_complexity") or "upper,lower,digit").split(","))
    checks = {"upper": any(c.isupper() for c in password), "lower": any(c.islower() for c in password),
              "digit": any(c.isdigit() for c in password), "special": any(not c.isalnum() for c in password)}
    if len(password) < minimum or len(password.encode("utf-8")) > 72 or any(not checks.get(rule.strip(), True) for rule in rules):
        raise HTTPException(422, f"密码必须满足配置的长度（至少{minimum}位，UTF-8不超过72字节）和复杂度要求")


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    # 检查账号是否启用
    if hasattr(user, 'is_active') and not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用，请联系管理员")
    # 记录登录时间
    user.last_login_at = datetime.utcnow()
    db.commit()
    from app.api.v1.system_config import _get_config_value
    timeout = _get_config_value(db, "auth.session_timeout")
    token = create_access_token(user.id, user.token_version, int(timeout) if timeout else None)
    refresh_token = create_refresh_token(user.id, user.token_version)
    return TokenResponse(
        token=token,
        refresh_token=refresh_token,
        user=UserOut(
            id=user.id, username=user.username, name=user.name,
            role=user.role, permissions=role_permissions(db, user.role),
        ),
    )


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    token: str
    refresh_token: str


@router.post("/refresh", response_model=RefreshResponse)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    user_id = decode_refresh_token(data.refresh_token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token 无效或已过期")
    user = db.get(User, user_id)
    payload = decode_token_payload(data.refresh_token, "refresh")
    if not user or not user.is_active or not payload or payload.get("tv", 0) != user.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    from app.api.v1.system_config import _get_config_value
    timeout = _get_config_value(db, "auth.session_timeout")
    new_token = create_access_token(user.id, user.token_version, int(timeout) if timeout else None)
    new_refresh = create_refresh_token(user.id, user.token_version)
    return RefreshResponse(token=new_token, refresh_token=new_refresh)


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(require_user), db: Session = Depends(get_db)):
    return UserOut(
        id=user.id, username=user.username, name=user.name,
        role=user.role, permissions=role_permissions(db, user.role),
    )


@router.post("/logout")
def logout(user: User = Depends(require_user), db: Session = Depends(get_db)):
    user.token_version += 1
    db.commit()
    return {"message": "所有会话已退出"}


# ── 用户管理（需 admin 权限）──

def _ensure_management_account(db, *, user_id=None, role=None, active=None, permission_role=None, permissions=None):
    """Do not let user or role editing remove the last management account."""
    for account in db.query(User).all():
        account_role = role if account.id == user_id and role is not None else account.role
        account_active = active if account.id == user_id and active is not None else account.is_active
        effective = permissions if account_role == permission_role else role_permissions(db, account_role)
        if account_active and "admin:users" in effective:
            return
    raise HTTPException(409, "必须保留至少一个启用且拥有系统管理权限的账号")

@router.get("/users", response_model=UserListResponse)
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=100),
    keyword: str | None = Query(None),
    role: str | None = Query(None),
    is_active: bool | None = Query(None),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    q = db.query(User)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(or_(User.username.ilike(like), User.name.ilike(like), User.email.ilike(like)))
    if role:
        q = q.filter(User.role == role)
    if is_active is not None:
        q = q.filter(User.is_active == is_active)

    total = q.count()
    items = q.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return UserListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/users", response_model=UserListItem)
def create_user(data: UserCreate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    validate_password(db, data.password)
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if data.role not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=400, detail=f"无效角色: {data.role}")
    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        name=data.name,
        email=data.email,
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=UserListItem)
def update_user(user_id: str, data: UserUpdate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if data.role is not None and data.role not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=400, detail=f"无效角色: {data.role}")
    _ensure_management_account(db, user_id=user.id, role=data.role, active=data.is_active)
    if data.name is not None:
        user.name = data.name
    if data.email is not None:
        user.email = data.email
    if data.role is not None:
        if user.role != data.role:
            user.token_version += 1
        user.role = data.role
    if data.is_active is not None:
        if user.is_active != data.is_active:
            user.token_version += 1
        user.is_active = data.is_active
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}/status")
def toggle_user_status(user_id: str, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    _ensure_management_account(db, user_id=user.id, active=not user.is_active)
    user.is_active = not user.is_active
    user.token_version += 1
    user.updated_at = datetime.utcnow()
    db.commit()
    return {"id": user.id, "is_active": user.is_active}


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: str, data: ResetPasswordRequest, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    validate_password(db, data.new_password)
    user.password_hash = hash_password(data.new_password)
    user.token_version += 1
    user.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "密码已重置"}


# ── 角色列表 ──

@router.get("/roles", response_model=list[RoleOut])
def list_roles(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    # 统计每个角色的用户数
    counts = dict(
        db.query(User.role, func.count(User.id)).group_by(User.role).all()
    )
    return [
        RoleOut(
            key=role_key,
            label=meta["label"],
            description=meta["description"],
            permissions=role_permissions(db, role_key),
            user_count=counts.get(role_key, 0),
            is_system=meta["is_system"],
        )
        for role_key, meta in ROLE_META.items()
    ]


@router.get("/permissions/modules")
def list_permission_modules(_admin: User = Depends(require_admin)):
    return PERMISSION_MODULES


class RolePermUpdate(BaseModel):
    permissions: list[str]


@router.put("/roles/{role_key}/permissions")
def update_role_permissions(role_key: str, data: RolePermUpdate, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """更新角色权限并持久化；后续请求立即读取当前配置。"""
    if role_key not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=404, detail="角色不存在")
    # 校验权限值合法性
    all_valid = set()
    for mod in PERMISSION_MODULES:
        all_valid.update(mod["permissions"])
    invalid = [p for p in data.permissions if p not in all_valid]
    if invalid:
        raise HTTPException(status_code=400, detail=f"无效权限: {', '.join(invalid)}")
    _ensure_management_account(db, permission_role=role_key, permissions=data.permissions)
    import json
    from app.models.system_config import SystemConfig
    key = f"auth.role_permissions.{role_key}"
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if row:
        row.value = json.dumps(data.permissions)
        row.updated_by = _admin.username
    else:
        db.add(SystemConfig(group="auth", key=key, value=json.dumps(data.permissions), updated_by=_admin.username))
    db.commit()
    return {"message": "权限已更新", "permissions": data.permissions}


def seed_admin(db: Session):
    """初始化管理员账号（仅首次创建，不重置已有密码）"""
    from app.config import settings
    existing = db.query(User).filter(User.username == "admin").first()
    if existing:
        return
    initial_pw = settings.ADMIN_INITIAL_PASSWORD
    if not initial_pw:
        raise RuntimeError("首次初始化必须配置 ADMIN_INITIAL_PASSWORD；不会创建使用默认密码的管理员")
    try:
        validate_password(db, initial_pw)
    except HTTPException as exc:
        raise RuntimeError(f"ADMIN_INITIAL_PASSWORD 不符合密码策略：{exc.detail}") from exc
    admin = User(
        username="admin",
        password_hash=hash_password(initial_pw),
        name="系统管理员",
        role="admin",
    )
    db.add(admin)
    db.commit()
