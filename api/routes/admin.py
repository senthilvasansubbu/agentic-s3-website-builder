"""
Admin / analytics routes — user-scoped activity only.
Platform-wide admin endpoints live in console.py (superuser-gated).
"""
from fastapi import APIRouter, Depends
from api.routes.auth import get_current_user
from services.analytics_service import get_user_activity

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/my-activity")
async def my_activity(limit: int = 50, current_user: dict = Depends(get_current_user)):
    return get_user_activity(current_user["sub"], limit)
