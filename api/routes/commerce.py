"""
Coupons, advertisements, and notification campaigns API.
"""
import uuid
import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Literal

from api.routes.auth import get_current_user
from database.snowflake_client import db
from services.notification_service import send_email, send_sms, send_whatsapp

router = APIRouter(prefix="/commerce", tags=["commerce"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _own_site(website_id: str, user_id: str):
    site = db.fetchone("SELECT user_id FROM websites WHERE website_id = ?", (website_id,))
    if not site:
        raise HTTPException(404, "Website not found")
    # Allow access if site owner or sub-user of owner
    if site["user_id"] != user_id:
        u = db.fetchone("SELECT owner_id FROM users WHERE user_id = ?", (user_id,))
        if not u or u.get("owner_id") != site["user_id"]:
            raise HTTPException(403, "Not your website")
    return site


# ── Coupon schemas ─────────────────────────────────────────────────────────────

class CouponCreate(BaseModel):
    website_id: str
    code: str
    discount_type: Literal["percent", "fixed"] = "percent"
    discount_value: float
    min_order: float = 0
    max_uses: int = 0
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None


class CouponUpdate(BaseModel):
    discount_value: Optional[float] = None
    min_order: Optional[float] = None
    max_uses: Optional[int] = None
    valid_until: Optional[str] = None
    is_active: Optional[int] = None


# ── Coupon endpoints ───────────────────────────────────────────────────────────

@router.get("/coupons/{website_id}")
async def list_coupons(website_id: str, current: dict = Depends(get_current_user)):
    _own_site(website_id, current["sub"])
    return db.execute(
        "SELECT * FROM coupons WHERE website_id = ? ORDER BY created_at DESC",
        (website_id,),
    ) or []


@router.post("/coupons")
async def create_coupon(body: CouponCreate, current: dict = Depends(get_current_user)):
    _own_site(body.website_id, current["sub"])
    existing = db.fetchone(
        "SELECT coupon_id FROM coupons WHERE website_id = ? AND code = ?",
        (body.website_id, body.code.upper()),
    )
    if existing:
        raise HTTPException(409, "Coupon code already exists for this website")

    cid = str(uuid.uuid4())
    db.execute(
        "INSERT INTO coupons (coupon_id, website_id, code, discount_type, discount_value, "
        "min_order, max_uses, valid_from, valid_until) VALUES (?,?,?,?,?,?,?,?,?)",
        (cid, body.website_id, body.code.upper(), body.discount_type, body.discount_value,
         body.min_order, body.max_uses, body.valid_from or "", body.valid_until or ""),
    )
    return {"coupon_id": cid, "code": body.code.upper()}


@router.patch("/coupons/{coupon_id}")
async def update_coupon(coupon_id: str, body: CouponUpdate,
                         current: dict = Depends(get_current_user)):
    row = db.fetchone("SELECT website_id FROM coupons WHERE coupon_id = ?", (coupon_id,))
    if not row:
        raise HTTPException(404, "Coupon not found")
    _own_site(row["website_id"], current["sub"])
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not updates:
        return {"message": "Nothing to update"}
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    db.execute(
        f"UPDATE coupons SET {set_clause} WHERE coupon_id = ?",
        (*updates.values(), coupon_id),
    )
    return {"message": "Coupon updated"}


@router.delete("/coupons/{coupon_id}")
async def delete_coupon(coupon_id: str, current: dict = Depends(get_current_user)):
    row = db.fetchone("SELECT website_id FROM coupons WHERE coupon_id = ?", (coupon_id,))
    if not row:
        raise HTTPException(404, "Coupon not found")
    _own_site(row["website_id"], current["sub"])
    db.execute("DELETE FROM coupons WHERE coupon_id = ?", (coupon_id,))
    return {"message": "Deleted"}


# ── Advertisement schemas ──────────────────────────────────────────────────────

class AdCreate(BaseModel):
    website_id: str
    title: str
    image_url: Optional[str] = None
    link_url: Optional[str] = None
    position: Literal["banner", "sidebar", "popup", "footer"] = "banner"
    starts_at: Optional[str] = None
    ends_at: Optional[str] = None


# ── Advertisement endpoints ────────────────────────────────────────────────────

@router.get("/ads/{website_id}")
async def list_ads(website_id: str, current: dict = Depends(get_current_user)):
    _own_site(website_id, current["sub"])
    return db.execute(
        "SELECT * FROM advertisements WHERE website_id = ? ORDER BY created_at DESC",
        (website_id,),
    ) or []


@router.post("/ads")
async def create_ad(body: AdCreate, current: dict = Depends(get_current_user)):
    _own_site(body.website_id, current["sub"])
    aid = str(uuid.uuid4())
    db.execute(
        "INSERT INTO advertisements (ad_id, website_id, title, image_url, link_url, position, starts_at, ends_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (aid, body.website_id, body.title, body.image_url or "", body.link_url or "",
         body.position, body.starts_at or "", body.ends_at or ""),
    )
    return {"ad_id": aid}


@router.delete("/ads/{ad_id}")
async def delete_ad(ad_id: str, current: dict = Depends(get_current_user)):
    row = db.fetchone("SELECT website_id FROM advertisements WHERE ad_id = ?", (ad_id,))
    if not row:
        raise HTTPException(404, "Ad not found")
    _own_site(row["website_id"], current["sub"])
    db.execute("DELETE FROM advertisements WHERE ad_id = ?", (ad_id,))
    return {"message": "Deleted"}


# ── Notification campaign schemas ──────────────────────────────────────────────

class CampaignCreate(BaseModel):
    website_id: str
    title: str
    channel: Literal["email", "sms", "whatsapp"]
    subject: Optional[str] = None
    body: str
    scheduled_at: Optional[str] = None


# ── Campaign endpoints ─────────────────────────────────────────────────────────

@router.get("/campaigns/{website_id}")
async def list_campaigns(website_id: str, current: dict = Depends(get_current_user)):
    _own_site(website_id, current["sub"])
    return db.execute(
        "SELECT * FROM notification_campaigns WHERE website_id = ? ORDER BY created_at DESC",
        (website_id,),
    ) or []


@router.post("/campaigns")
async def create_campaign(body: CampaignCreate, current: dict = Depends(get_current_user)):
    _own_site(body.website_id, current["sub"])
    cid = str(uuid.uuid4())
    db.execute(
        "INSERT INTO notification_campaigns "
        "(campaign_id, website_id, owner_id, title, channel, subject, body, scheduled_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (cid, body.website_id, current["sub"], body.title, body.channel,
         body.subject or "", body.body, body.scheduled_at or ""),
    )
    return {"campaign_id": cid}


@router.post("/campaigns/{campaign_id}/send")
async def send_campaign(campaign_id: str, current: dict = Depends(get_current_user)):
    """Send a campaign to all customers who gave feedback on the website (have emails)."""
    camp = db.fetchone(
        "SELECT * FROM notification_campaigns WHERE campaign_id = ? AND owner_id = ?",
        (campaign_id, current["sub"]),
    )
    if not camp:
        raise HTTPException(404, "Campaign not found")

    # Collect recipient emails/mobiles from feedback
    recipients = db.execute(
        "SELECT DISTINCT email, name FROM feedback WHERE website_id = ? AND email != ''",
        (camp["website_id"],),
    ) or []

    sent = 0
    for r in recipients:
        dest = r.get("email", "")
        if not dest:
            continue
        try:
            if camp["channel"] == "email":
                send_email(dest, camp["subject"] or camp["title"],
                           f"<p>{camp['body']}</p>", current["sub"])
            elif camp["channel"] == "sms":
                send_sms(dest, camp["body"], current["sub"])
            elif camp["channel"] == "whatsapp":
                send_whatsapp(dest, camp["body"], current["sub"])
            sent += 1
        except Exception:
            pass

    import datetime
    db.execute(
        "UPDATE notification_campaigns SET status='sent', sent_count=?, sent_at=? WHERE campaign_id=?",
        (sent, datetime.datetime.utcnow().isoformat(), campaign_id),
    )
    return {"message": f"Campaign sent to {sent} recipient(s)"}


@router.delete("/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: str, current: dict = Depends(get_current_user)):
    row = db.fetchone(
        "SELECT campaign_id FROM notification_campaigns WHERE campaign_id = ? AND owner_id = ?",
        (campaign_id, current["sub"]),
    )
    if not row:
        raise HTTPException(404, "Campaign not found")
    db.execute("DELETE FROM notification_campaigns WHERE campaign_id = ?", (campaign_id,))
    return {"message": "Deleted"}
