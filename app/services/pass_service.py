"""Issuing, rendering and distributing guest passes."""
import hashlib
import html
import io
import json
import secrets
import zipfile
from datetime import datetime, timezone

import httpx
from cryptography.fernet import Fernet
import base64
import qrcode
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, A6, landscape, portrait
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from sqlmodel import Session, select

from app.core.config import settings
from app.models.event import Event
from app.models.eventGuest import EventGuest, EventGuestStatus
from app.models.eventAccessLevel import EventAccessLevel
from app.models.guest import Guest
from app.models.passes import Pass, PassStatus, EventPassTemplate
from app.models.eventCustomField import EventCustomField

ELIGIBLE_STATUSES = {EventGuestStatus.REGISTERED, EventGuestStatus.CONFIRMED, EventGuestStatus.APPROVED}


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256((settings.PASS_ENCRYPTION_KEY or settings.JWT_SECRET_KEY).encode("utf-8")).digest())
    return Fernet(key)


def encrypt_qr_token(token: str) -> str:
    return _fernet().encrypt(token.encode("utf-8")).decode("ascii")


def decrypt_qr_token(token: str | None) -> str:
    if not token:
        raise HTTPException(status_code=409, detail="Pass QR credential is unavailable")
    return _fernet().decrypt(token.encode("ascii")).decode("utf-8")


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_event(db: Session, event_id: int, organization_id: int) -> Event:
    event = db.exec(select(Event).where(Event.id == event_id, Event.organization_id == organization_id)).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def get_template(db: Session, event_id: int) -> EventPassTemplate:
    template = db.exec(select(EventPassTemplate).where(EventPassTemplate.event_id == event_id)).first()
    if template:
        return template
    template = EventPassTemplate(event_id=event_id)
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def issue_pass(db: Session, registration: EventGuest) -> tuple[Pass, str | None]:
    existing = db.exec(select(Pass).where(Pass.event_guest_id == registration.id, Pass.status == PassStatus.ACTIVE)).first()
    if existing:
        return existing, None
    qr_token = secrets.token_urlsafe(32)
    download_token = secrets.token_urlsafe(32)
    code = f"LK-{secrets.token_hex(5).upper()}"
    item = Pass(event_guest_id=registration.id, code=code, pass_token_hash=token_hash(qr_token), qr_token_encrypted=encrypt_qr_token(qr_token), download_token_hash=token_hash(download_token), download_token_encrypted=encrypt_qr_token(download_token))
    db.add(item)
    try:
        db.commit()
        db.refresh(item)
        return item, download_token
    except IntegrityError:
        db.rollback()
        existing = db.exec(select(Pass).where(Pass.event_guest_id == registration.id, Pass.status == PassStatus.ACTIVE)).first()
        if existing:
            return existing, None
        raise


def pass_payload(db: Session, item: Pass) -> dict:
    registration = db.get(EventGuest, item.event_guest_id)
    guest = db.get(Guest, registration.guest_id) if registration else None
    event = db.get(Event, registration.event_id) if registration else None
    access = db.get(EventAccessLevel, registration.access_level_id) if registration and registration.access_level_id else None
    template = get_template(db, event.id) if event else None
    config = json.loads(template.config_json) if template else {}
    return {"pass": item, "registration": registration, "guest": guest, "event": event, "access": access, "template": config, "orientation": template.orientation if template else "portrait", "design": template.design if template else "professional"}


def render_pdf(db: Session, item: Pass, qr_value: str) -> bytes:
    data = pass_payload(db, item)
    guest, event, access = data["guest"], data["event"], data["access"]
    cfg = data["template"]
    if not guest or not event:
        raise HTTPException(status_code=404, detail="Pass details not found")
    orientation = data["orientation"]
    page = landscape(A6) if orientation == "landscape" else portrait(A6)
    stream = io.BytesIO()
    pdf = canvas.Canvas(stream, pagesize=page)
    width, height = page
    bg = cfg.get("backgroundColor", "#FFFFFF")
    fg = cfg.get("textColor", "#172322")
    accent = cfg.get("accentColor", "#0F766E")
    try:
        pdf.setFillColor(colors.HexColor(bg)); pdf.rect(0, 0, width, height, fill=1, stroke=0)
    except ValueError:
        pdf.setFillColor(colors.white); pdf.rect(0, 0, width, height, fill=1, stroke=0)
    header_height = 72 if data["design"] == "creative" else 54
    pdf.setFillColor(colors.HexColor(accent)); pdf.rect(0, height-header_height, width, header_height, fill=1, stroke=0)
    pdf.setFillColor(colors.white); pdf.setFont("Helvetica-Bold", 15 if data["design"] == "creative" else 13)
    heading = (cfg.get("title") or event.name)[:42]
    if data["design"] == "creative":
        pdf.drawCentredString(width / 2, height - 43, heading)
        pdf.setFont("Helvetica", 7); pdf.drawCentredString(width / 2, height - 57, "YOUR EVENT ACCESS PASS")
    else:
        pdf.drawString(24, height - 33, heading)
    pdf.setFillColor(colors.HexColor(fg))
    y = height - (header_height + 34)
    pdf.setFont("Helvetica-Bold", 17); pdf.drawString(24, y, guest.full_name[:34]); y -= 25
    pdf.setFont("Helvetica", 10)
    fields = [("event", "EVENT", event.name), ("date", "DATE", event.start_at.strftime("%d %b %Y, %H:%M") if event.start_at else "To be announced"), ("venue", "VENUE", event.venue_name or event.venue_address or "To be announced"), ("access", "ACCESS", access.name if access else "General Admission"), ("code", "PASS CODE", item.code)]
    visibility = cfg.get("visibleFields", ["event", "date", "venue", "access", "code"])
    field_step = 27 if orientation == "landscape" else 36
    value_limit = 34 if orientation == "landscape" else 55
    for field_key, label, value in fields:
        if field_key not in visibility:
            continue
        pdf.setFillColor(colors.HexColor(accent)); pdf.setFont("Helvetica-Bold", 7); pdf.drawString(24, y, label)
        pdf.setFillColor(colors.HexColor(fg)); pdf.setFont("Helvetica", 9); pdf.drawString(24, y-11, str(value or "")[:value_limit]); y -= field_step
    selected_custom = cfg.get("customFieldKeys", [])
    if selected_custom and data["registration"] and orientation != "landscape" and y > 150:
        try:
            custom_values = json.loads(data["registration"].custom_field_values or "{}")
        except (TypeError, ValueError):
            custom_values = {}
        definitions = db.exec(select(EventCustomField).where(EventCustomField.event_id == event.id, EventCustomField.field_key.in_(selected_custom), EventCustomField.is_active.is_(True))).all()
        for definition in definitions:
            if y < 145:
                break
            value = custom_values.get(definition.field_key)
            if value is None or value == "":
                continue
            pdf.setFillColor(colors.HexColor(accent)); pdf.setFont("Helvetica-Bold", 7); pdf.drawString(24, y, definition.label[:40].upper())
            pdf.setFillColor(colors.HexColor(fg)); pdf.setFont("Helvetica", 9); pdf.drawString(24, y-13, str(value)[:55]); y -= 32
    qr = qrcode.QRCode(box_size=5, border=2); qr.add_data(qr_value); qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white")
    qr_bytes = io.BytesIO(); qr_image.save(qr_bytes, format="PNG"); qr_bytes.seek(0)
    qr_size = min(105, width * .34)
    pdf.drawImage(ImageReader(qr_bytes), width-qr_size-22, 28, qr_size, qr_size, preserveAspectRatio=True, mask="auto")
    pdf.setFont("Helvetica", 7); pdf.setFillColor(colors.HexColor(fg)); pdf.drawString(24, 28, "Present this pass at event entry")
    pdf.showPage(); pdf.save()
    return stream.getvalue()


def send_pass_email(to_email: str, guest_name: str, event_name: str, download_url: str) -> None:
    if not settings.RESEND_API_KEY:
        raise HTTPException(status_code=503, detail="Email delivery is not configured. Set RESEND_API_KEY.")
    safe_name, safe_event, safe_url = html.escape(guest_name), html.escape(event_name), html.escape(download_url, quote=True)
    payload = {"from": settings.RESEND_FROM_EMAIL, "to": [to_email], "subject": f"Your pass for {event_name}", "html": f'''<div style="font-family:Arial,sans-serif;max-width:560px;margin:32px auto;padding:28px;border:1px solid #e5e7eb;border-radius:16px"><p style="color:#0f766e;font-weight:bold;letter-spacing:2px">LIINKE</p><h2>Your event pass is ready</h2><p>Hello {safe_name},</p><p>Your pass for <strong>{safe_event}</strong> is ready to download.</p><p><a href="{safe_url}" style="display:inline-block;background:#0f766e;color:#fff;padding:13px 20px;border-radius:8px;text-decoration:none">Download my pass</a></p><p style="font-size:12px;color:#64748b">Keep this pass private. It contains your unique event entry QR code.</p></div>'''}
    try:
        response = httpx.post("https://api.resend.com/emails", headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}", "Content-Type": "application/json"}, json=payload, timeout=15)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Email delivery failed. You can retry sending the pass.") from exc


def make_zip(db: Session, passes: list[Pass]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in passes:
            # QR is derived from a separately generated raw credential. Existing hashed credentials
            # cannot be reversed, so ZIP generation uses a fresh credential only after rotation.
            qr_token = decrypt_qr_token(item.qr_token_encrypted)
            archive.writestr(f"{item.code}.pdf", render_pdf(db, item, f"LIINKE:PASS:{qr_token}"))
        db.commit()
    output.seek(0)
    return output.getvalue()
