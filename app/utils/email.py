"""Resend email delivery for organization invitations."""
import html
import httpx
from fastapi import HTTPException, status

from app.core.config import settings


def send_organization_invitation(
    *,
    to_email: str,
    organization_name: str,
    inviter_name: str | None,
    role: str,
    invitation_url: str,
) -> None:
    if not settings.RESEND_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email delivery is not configured. Set RESEND_API_KEY.",
        )
    if not settings.RESEND_FROM_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email sender is not configured. Set RESEND_FROM_EMAIL.",
        )

    org = html.escape(organization_name)
    inviter = html.escape(inviter_name or "Your organization administrator")
    safe_role = html.escape(role.title())
    safe_url = html.escape(invitation_url, quote=True)

    payload = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": [to_email],
        "subject": f"You've been invited to join {organization_name} on Liinke",
        "html": f"""
        <!doctype html>
        <html>
          <body style="margin:0;background:#f5f7f7;font-family:Arial,sans-serif;color:#172322">
            <div style="max-width:560px;margin:40px auto;background:#fff;padding:36px;border-radius:18px">
              <p style="color:#0d9488;font-weight:700;letter-spacing:2px">LIINKE</p>
              <h1 style="font-size:26px">You're invited to join {org}</h1>
              <p>{inviter} invited you to collaborate with <strong>{org}</strong>
                 as a <strong>{safe_role}</strong>.</p>
              <p style="margin:30px 0">
                <a href="{safe_url}" style="background:#0f766e;color:#fff;text-decoration:none;
                   padding:14px 22px;border-radius:9px;display:inline-block;font-weight:700">
                  Accept invitation
                </a>
              </p>
              <p style="font-size:13px;color:#64748b">This invitation expires in 7 days.
                 If you were not expecting it, you can ignore this email.</p>
              <p style="font-size:12px;color:#94a3b8;word-break:break-all">{safe_url}</p>
            </div>
          </body>
        </html>
        """,
    }

    try:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        # Do not expose the provider response or API key to the client.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The invitation was created, but Resend could not deliver the email. You can retry sending it.",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The invitation was created, but email delivery failed. You can retry sending it.",
        ) from exc
