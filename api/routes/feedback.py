"""Feedback API — collect and retrieve website visitor feedback."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid, datetime
from slowapi import Limiter
from slowapi.util import get_remote_address

from database.snowflake_client import db
from api.routes.auth import get_current_user

router = APIRouter(prefix="/feedback", tags=["feedback"])
limiter = Limiter(key_func=get_remote_address)


class FeedbackSubmit(BaseModel):
    name: Optional[str] = "Anonymous"
    email: Optional[str] = None
    rating: int = 5          # 1-5
    message: Optional[str] = None


@router.post("/{website_id}")
@limiter.limit("10/minute")
async def submit_feedback(website_id: str, body: FeedbackSubmit, request: Request):
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
async def get_feedback(website_id: str, current_user: dict = Depends(get_current_user)):
    """Only the website owner (or superuser) can read feedback."""
    # Verify website ownership
    site = db.fetchone("SELECT user_id FROM websites WHERE website_id = ?", (website_id,))
    if not site:
        raise HTTPException(status_code=404, detail="Website not found")
    if current_user.get("role") != "superuser" and site["user_id"] != current_user["sub"]:
        # Also allow the client user assigned to this website
        u = db.fetchone("SELECT client_website_id, owner_id FROM users WHERE user_id = ?", (current_user["sub"],))
        is_client_of_site = u and u.get("client_website_id") == website_id
        is_subuser = u and db.fetchone(
            "SELECT user_id FROM websites WHERE website_id = ? AND user_id = ?",
            (website_id, u.get("owner_id"))
        )
        if not is_client_of_site and not is_subuser:
            raise HTTPException(status_code=403, detail="Access denied")

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
