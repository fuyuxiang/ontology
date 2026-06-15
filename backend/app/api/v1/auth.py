from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest, TokenResponse, UserOut, ROLE_PERMISSIONS, ROLE_META, PERMISSION_MODULES,
    UserListItem, UserListResponse, UserCreate, UserUpdate, ResetPasswordRequest, RoleOut,
)
from app.core.security import verify_password, create_access_token, create_refresh_token, decode_refresh_token, hash_password
from app.core.deps import require_user, require_admin

router = APIRouter(prefix="/auth", tags=["auth"])


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
    token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    return TokenResponse(
        token=token,
        refresh_token=refresh_token,
        user=UserOut(
            id=user.id, username=user.username, name=user.name,
            role=user.role, permissions=ROLE_PERMISSIONS.get(user.role, []),
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
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    new_token = create_access_token(user.id)
    new_refresh = create_refresh_token(user.id)
    return RefreshResponse(token=new_token, refresh_token=new_refresh)


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(require_user)):
    return UserOut(
        id=user.id, username=user.username, name=user.name,
        role=user.role, permissions=ROLE_PERMISSIONS.get(user.role, []),
    )


# ── 用户管理（需 admin 权限）──

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
    if data.name is not None:
        user.name = data.name
    if data.email is not None:
        user.email = data.email
    if data.role is not None:
        if data.role not in ROLE_PERMISSIONS:
            raise HTTPException(status_code=400, detail=f"无效角色: {data.role}")
        user.role = data.role
    if data.is_active is not None:
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
    user.is_active = not user.is_active
    user.updated_at = datetime.utcnow()
    db.commit()
    return {"id": user.id, "is_active": user.is_active}


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: str, data: ResetPasswordRequest, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.password_hash = hash_password(data.new_password)
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
            permissions=ROLE_PERMISSIONS.get(role_key, []),
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
def update_role_permissions(role_key: str, data: RolePermUpdate, _admin: User = Depends(require_admin)):
    """更新角色权限（运行时生效，重启后恢复默认；后续可持久化到数据库）"""
    if role_key not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=404, detail="角色不存在")
    # 校验权限值合法性
    all_valid = set()
    for mod in PERMISSION_MODULES:
        all_valid.update(mod["permissions"])
    invalid = [p for p in data.permissions if p not in all_valid]
    if invalid:
        raise HTTPException(status_code=400, detail=f"无效权限: {', '.join(invalid)}")
    ROLE_PERMISSIONS[role_key] = data.permissions
    ROLE_META[role_key]["description"] = ROLE_META[role_key].get("description", "")
    return {"message": "权限已更新", "permissions": data.permissions}


def seed_admin(db: Session):
    """初始化管理员账号（仅首次创建，不重置已有密码）"""
    from app.config import settings
    existing = db.query(User).filter(User.username == "admin").first()
    if existing:
        return
    initial_pw = settings.ADMIN_INITIAL_PASSWORD
    if not initial_pw:
        initial_pw = "admin"
    admin = User(
        username="admin",
        password_hash=hash_password(initial_pw),
        name="系统管理员",
        role="admin",
    )
    db.add(admin)
    db.commit()
