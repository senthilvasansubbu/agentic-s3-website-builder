"""Chatbot API — AI-powered assistant for admin console and website visitors."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os

from database.snowflake_client import db

router = APIRouter(prefix="/chatbot", tags=["chatbot"])


class ChatRequest(BaseModel):
    message: str
    website_id: Optional[str] = None
    context: Optional[str] = "visitor"   # visitor | admin_console


class ChatResponse(BaseModel):
    reply: str


def _llm_reply(prompt: str) -> str:
    """Call OpenAI if key present, otherwise return a rule-based response."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key:
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful AI assistant for an AI website builder SaaS platform. "
                            "Help users with questions about building websites, managing products, "
                            "setting up payments, and using the platform. Be concise and friendly."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=512,
                temperature=0.7,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"AI service temporarily unavailable. ({e})"

    # ── Rule-based fallback ──────────────────────────────────────────────────
    msg = prompt.lower()
    if any(w in msg for w in ("hello", "hi", "hey")):
        return "Hello! 👋 I'm your AI assistant. Ask me anything about building websites or managing your platform."
    if "plan" in msg or "price" in msg or "cost" in msg:
        return "We offer three plans:\n• **Free** — up to 10 pages, basic features\n• **Pro** — unlimited pages, shopping cart, custom domain\n• **Enterprise** — all Pro features + analytics, team access"
    if "theme" in msg:
        return "Available themes: modern, classic, minimal, dark, nature, ecommerce. You can select a theme when creating or editing a website."
    if "payment" in msg or "stripe" in msg:
        return "Payments are handled via Stripe. Configure your Stripe API keys in Settings → Payment Config to enable checkout on your websites."
    if "user" in msg and "create" in msg:
        return "To create a user: go to Users → click '+Create User', fill in their name, email, temporary password and plan, then click 'Create User'."
    if "website" in msg and ("build" in msg or "creat" in msg):
        return "To build a website: go to Websites → '+New Website', enter the name, pick a theme, and click Build. The AI will generate content automatically."
    if "password" in msg:
        return "You can change your password in Settings → 'Change Admin Password'."
    if "s3" in msg or "deploy" in msg or "host" in msg:
        return "Set your AWS credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME) in the .env file to enable S3 deployment."
    if "feedback" in msg:
        return "Customer feedback is displayed in the Feedback section. Each website also exposes a public POST /api/v1/feedback/{website_id} endpoint for visitors to submit reviews."
    return (
        "I'm here to help with website building, user management, payments, and platform setup. "
        "Could you rephrase your question or be more specific?"
    )


def _build_prompt(msg: str, context: str, website_data: dict | None) -> str:
    """Enrich the message with website context if available."""
    if context == "admin_console":
        return f"Admin console question: {msg}"
    if website_data:
        return (
            f"Website: {website_data.get('name', 'Unknown')} "
            f"(theme: {website_data.get('theme', 'modern')}, "
            f"description: {website_data.get('description', 'N/A')})\n"
            f"Visitor question: {msg}"
        )
    return msg


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    if not body.message or not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    website_data = None
    if body.website_id:
        rows = db.execute(
            "SELECT name, theme, description FROM websites WHERE website_id=?",
            [body.website_id],
        )
        website_data = (rows or [None])[0]

    prompt = _build_prompt(body.message.strip(), body.context or "visitor", website_data)
    reply = _llm_reply(prompt)
    return ChatResponse(reply=reply)


@router.post("/{website_id}", response_model=ChatResponse)
async def chat_for_website(website_id: str, body: ChatRequest):
    """Public endpoint for website visitor chatbot."""
    body.website_id = website_id
    body.context = "visitor"
    return await chat(body)
