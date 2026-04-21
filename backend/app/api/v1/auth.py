from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut, ROLE_PERMISSIONS
from app.core.security import verify_password, create_access_token, hash_password
from app.core.deps import require_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    token = create_access_token(user.id)
    return TokenResponse(
        token=token,
        user=UserOut(
            id=user.id, username=user.username, name=user.name,
            role=user.role, permissions=ROLE_PERMISSIONS.get(user.role, []),
        ),
    )


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(require_user)):
    return UserOut(
        id=user.id, username=user.username, name=user.name,
        role=user.role, permissions=ROLE_PERMISSIONS.get(user.role, []),
    )


def seed_admin(db: Session):
    """初始化管理员账号"""
    existing = db.query(User).filter(User.username == "admin").first()
    if existing:
        existing.password_hash = hash_password("bonc")
        db.commit()
        return
    admin = User(
        username="admin",
        password_hash=hash_password("bonc"),
        name="系统管理员",
        role="admin",
    )
    db.add(admin)
    db.commit()
