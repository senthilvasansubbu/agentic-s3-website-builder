"""
OTP delivery service — sends OTP via email (SMTP/SendGrid) or SMS (Twilio).
"""
import os
import smtplib
from email.mime.text import MIMEText
from typing import Literal

# ── Email via SMTP / SendGrid ─────────────────────────────────────────────────

def send_otp_email(to_email: str, otp_code: str, site_name: str = "Website Builder") -> bool:
    """Send OTP via SMTP.  Configure SMTP_* env vars or use SendGrid relay."""
    smtp_host   = os.getenv("SMTP_HOST", "smtp.sendgrid.net")
    smtp_port   = int(os.getenv("SMTP_PORT", "587"))
    smtp_user   = os.getenv("SMTP_USER", "apikey")
    smtp_pass   = os.getenv("SMTP_PASSWORD", "")
    from_email  = os.getenv("SMTP_FROM", "noreply@websitebuilder.ai")

    body = f"""
    <html><body>
    <h2>Your {site_name} verification code</h2>
    <p style="font-size:32px;font-weight:bold;letter-spacing:6px">{otp_code}</p>
    <p>This code expires in <strong>10 minutes</strong>.</p>
    <p>If you did not request this code, please ignore this email.</p>
    </body></html>
    """
    msg = MIMEText(body, "html")
    msg["Subject"] = f"[{site_name}] Your OTP: {otp_code}"
    msg["From"]    = from_email
    msg["To"]      = to_email

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, [to_email], msg.as_string())
        return True
    except Exception as exc:
        print(f"[OTP] Email send failed: {exc}")
        return False


# ── SMS via Twilio ────────────────────────────────────────────────────────────

def send_otp_sms(to_mobile: str, otp_code: str, site_name: str = "Website Builder") -> bool:
    """Send OTP via Twilio SMS."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token  = os.getenv("TWILIO_AUTH_TOKEN", "")
    from_number = os.getenv("TWILIO_FROM_NUMBER", "")

    if not (account_sid and auth_token and from_number):
        print("[OTP] Twilio credentials not configured.")
        return False

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        client.messages.create(
            body=f"[{site_name}] Your OTP: {otp_code}. Valid for 10 minutes.",
            from_=from_number,
            to=to_mobile,
        )
        return True
    except Exception as exc:
        print(f"[OTP] SMS send failed: {exc}")
        return False


def deliver_otp(
    channel: Literal["email", "sms"],
    destination: str,
    otp_code: str,
    site_name: str = "Website Builder",
) -> bool:
    if channel == "email":
        return send_otp_email(destination, otp_code, site_name)
    return send_otp_sms(destination, otp_code, site_name)
