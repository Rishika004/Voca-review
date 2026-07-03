import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = (os.getenv("GMAIL_APP_PASSWORD") or "").replace(" ", "")
MEET_LINK = os.getenv("MEET_LINK", "https://meet.google.com/byn-mezv-ddv")


def send_meeting_confirmation(
    lead_name: str,
    lead_email: str,
    meeting_time: str,
    notify_email: str,
) -> bool:
    """
    Sends two emails:
    1. Confirmation to the lead (lead_email)
    2. Notification to you (notify_email)
    Returns True if sent successfully.
    """
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        logger.warning("Gmail credentials not set — skipping email")
        return False

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)

            # --- Email 1: to the lead ---
            lead_msg = MIMEMultipart("alternative")
            lead_msg["Subject"] = "Your Karta Demo is Confirmed!"
            lead_msg["From"] = GMAIL_USER
            lead_msg["To"] = lead_email

            lead_html = f"""
            <div style="font-family:sans-serif;max-width:520px;margin:auto;padding:32px;background:#f9f9f9;border-radius:12px;">
              <div style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:20px 24px;border-radius:8px;margin-bottom:24px;">
                <h2 style="color:#fff;margin:0;">Your Demo is Confirmed ✅</h2>
              </div>
              <p style="color:#333;font-size:16px;">Hi <strong>{lead_name}</strong>,</p>
              <p style="color:#555;">Thank you for speaking with <strong>Aria</strong> from Karta! Your demo has been booked.</p>
              <div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:20px;margin:20px 0;">
                <p style="margin:0;color:#6366f1;font-weight:700;font-size:14px;text-transform:uppercase;letter-spacing:1px;">Meeting Details</p>
                <p style="font-size:22px;font-weight:700;color:#1e1e35;margin:8px 0;">{meeting_time}</p>
                <a href="{MEET_LINK}" style="display:inline-block;margin-top:12px;background:#6366f1;color:#fff;text-decoration:none;padding:12px 24px;border-radius:8px;font-weight:700;font-size:15px;">Join Google Meet</a>
                <p style="color:#777;margin:12px 0 0;font-size:12px;">Link: {MEET_LINK}</p>
              </div>
              <p style="color:#555;">We're excited to show you how Karta can automate your customer support and help you scale.</p>
              <p style="color:#999;font-size:12px;margin-top:32px;">— Aria, Karta AI Agent</p>
            </div>
            """
            lead_msg.attach(MIMEText(lead_html, "html"))
            server.sendmail(GMAIL_USER, lead_email, lead_msg.as_string())
            logger.info(f"Confirmation email sent to lead: {lead_email}")

            # --- Email 2: notification to you ---
            notif_msg = MIMEMultipart("alternative")
            notif_msg["Subject"] = f"New Demo Booked — {lead_name} ({meeting_time})"
            notif_msg["From"] = GMAIL_USER
            notif_msg["To"] = notify_email

            notif_html = f"""
            <div style="font-family:sans-serif;max-width:520px;margin:auto;padding:32px;background:#f9f9f9;border-radius:12px;">
              <div style="background:#1e1e35;padding:20px 24px;border-radius:8px;margin-bottom:24px;">
                <h2 style="color:#a5f3fc;margin:0;">📞 New Demo Booked</h2>
              </div>
              <table style="width:100%;border-collapse:collapse;font-size:15px;">
                <tr><td style="padding:10px;color:#888;width:120px;">Lead Name</td><td style="padding:10px;font-weight:600;color:#1e1e35;">{lead_name}</td></tr>
                <tr style="background:#f3f4f6;"><td style="padding:10px;color:#888;">Email</td><td style="padding:10px;color:#1e1e35;">{lead_email}</td></tr>
                <tr><td style="padding:10px;color:#888;">Meeting</td><td style="padding:10px;font-weight:700;color:#6366f1;">{meeting_time}</td></tr>
                <tr><td style="padding:10px;color:#888;">Meet Link</td><td style="padding:10px;"><a href="{MEET_LINK}" style="color:#6366f1;">{MEET_LINK}</a></td></tr>
              </table>
              <p style="color:#999;font-size:12px;margin-top:32px;">Sent automatically by Aria — Karta AI Agent</p>
            </div>
            """
            notif_msg.attach(MIMEText(notif_html, "html"))
            server.sendmail(GMAIL_USER, notify_email, notif_msg.as_string())
            logger.info(f"Notification email sent to: {notify_email}")

        return True

    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False
