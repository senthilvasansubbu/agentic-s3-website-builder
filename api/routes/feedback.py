"""Feedback API — collect and retrieve website visitor feedback."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid, datetime

from database.snowflake_client import db

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackSubmit(BaseModel):
    name: Optional[str] = "Anonymous"
    email: Optional[str] = None
    rating: int = 5          # 1-5
    message: Optional[str] = None


@router.post("/{website_id}")
async def submit_feedback(website_id: str, body: FeedbackSubmit):
    if not 1 <= body.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5")

    feedback_id = str(uuid.uuid4())
    now = datetime.datetime.utcnow().isoformat()
    db.execute(
        "INSERT INTO feedback (feedback_id, website_id, name, email, rating, message, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        [feedback_id, website_id, body.name, body.email, body.rating, body.message, now],
    )
    return {"feedback_id": feedback_id, "message": "Thank you for your feedback!"}


@router.get("/{website_id}")
async def get_feedback(website_id: str):
    rows = db.execute(
        "SELECT feedback_id, name, rating, message, created_at "
        "FROM feedback WHERE website_id=? ORDER BY created_at DESC LIMIT 50",
        [website_id],
    )
    avg_row = db.execute(
        "SELECT AVG(CAST(rating AS FLOAT)) AS avg_rating, COUNT(*) AS total "
        "FROM feedback WHERE website_id=?",
        [website_id],
    )
    avg = (avg_row or [{}])[0]
    return {
        "average_rating": round(avg.get("avg_rating") or 0, 1),
        "total": avg.get("total", 0),
        "reviews": rows or [],
    }
