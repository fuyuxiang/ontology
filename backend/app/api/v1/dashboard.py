from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories import DashboardRepository

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    repo = DashboardRepository(db)
    return repo.get_stats()
