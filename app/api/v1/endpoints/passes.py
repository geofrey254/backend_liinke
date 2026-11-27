import hmac
import json
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlmodel import select

from app.core.dependencies import get_current_membership, require_organization_admin
from app.database.session import SessionDep
from app.models.event import Event
from app.models.eventGuest import EventGuest, EventGuestStatus
from app.models.guest import Guest
from app.models.passes import Pass, PassStatus
from app.models.eventCustomField import EventCustomField
from app.models.organizationMembership import OrganizationMembership
from app.services.pass_service import (
    ELIGIBLE_STATUSES, decrypt_qr_token, get_event, get_template, issue_pass,
    make_zip, pass_payload, render_pdf, send_pass_email, token_hash,
)

router = APIRouter()


class GeneratePassesRequest(BaseModel):
    guest_ids: list[int] | None = None


class PassTemplateUpdate(BaseModel):
    design: str = Field(default="professional", pattern="^(professional|creative)$")
    orientation: str = Field(default="portrait", pattern="^(portrait|landscape)$")
    config: dict = Field(default_factory=dict)


@router.get("/events/{event_id}/pass-template")
def read_pass_template(event_id: int, db: SessionDep, membership: Annotated[OrganizationMembership, Depends(get_current_membership)]):
    get_event(db, event_id, membership.organization_id)
    template = get_template(db, event_id)
    return {"design": template.design, "orientation": template.orientation, "config": json.loads(template.config_json), "version": template.version, "availableCustomFields": [{"field_key": f.field_key, "label": f.label} for f in db.exec(select(EventCustomField).where(EventCustomField.event_id == event_id, EventCustomField.is_active.is_(True))).all()]}


@router.put("/events/{event_id}/pass-template")
def update_pass_template(event_id: int, body: PassTemplateUpdate, db: SessionDep, membership: Annotated[OrganizationMembership, Depends(get_current_membership)], _: Annotated[None, Depends(require_organization_admin)]):
    get_event(db, event_id, membership.organization_id)
    allowed = {"title", "backgroundColor", "textColor", "accentColor", "visibleFields", "customFieldKeys"}
    if set(body.config) - allowed:
        raise HTTPException(status_code=422, detail="Unsupported pass template fields")
    for key in ("backgroundColor", "textColor", "accentColor"):
        value = body.config.get(key)
        if value is not None and (not isinstance(value, str) or not __import__("re").fullmatch(r"#[0-9a-fA-F]{6}", value)):
            raise HTTPException(status_code=422, detail=f"{key} must be a six-digit hex color")
    if "visibleFields" in body.config and (not isinstance(body.config["visibleFields"], list) or any(x not in {"event", "date", "venue", "access", "code"} for x in body.config["visibleFields"])):
        raise HTTPException(status_code=422, detail="Invalid visibleFields")
    if "customFieldKeys" in body.config:
        if not isinstance(body.config["customFieldKeys"], list) or any(not isinstance(x, str) for x in body.config["customFieldKeys"]):
            raise HTTPException(status_code=422, detail="customFieldKeys must be a list of field keys")
        available = {field.field_key for field in db.exec(select(EventCustomField).where(EventCustomField.event_id == event_id, EventCustomField.is_active.is_(True))).all()}
        if set(body.config["customFieldKeys"]) - available:
            raise HTTPException(status_code=422, detail="One or more selected custom fields do not belong to this event")
    template = get_template(db, event_id)
    template.design, template.orientation = body.design, body.orientation
    template.config_json = json.dumps(body.config)
    template.version += 1
    template.updated_at = datetime.now(timezone.utc)
    db.add(template); db.commit(); db.refresh(template)
    return {"design": template.design, "orientation": template.orientation, "config": body.config, "version": template.version, "availableCustomFields": [{"field_key": f.field_key, "label": f.label} for f in db.exec(select(EventCustomField).where(EventCustomField.event_id == event_id, EventCustomField.is_active.is_(True))).all()]}


@router.post("/events/{event_id}/passes/generate")
def generate_passes(event_id: int, body: GeneratePassesRequest, db: SessionDep, membership: Annotated[OrganizationMembership, Depends(get_current_membership)], _: Annotated[None, Depends(require_organization_admin)]):
    get_event(db, event_id, membership.organization_id)
    statement = select(EventGuest).where(EventGuest.event_id == event_id, EventGuest.registration_status.in_(ELIGIBLE_STATUSES))
    if body.guest_ids is not None:
        if not body.guest_ids:
            raise HTTPException(status_code=422, detail="Select at least one guest")
        statement = statement.where(EventGuest.guest_id.in_(set(body.guest_ids)))
    registrations = db.exec(statement.order_by(EventGuest.id)).all()
    created, existing, skipped = [], 0, 0
    for registration in registrations:
        guest = db.get(Guest, registration.guest_id)
        if not guest or guest.organization_id != membership.organization_id:
            skipped += 1; continue
        item, download_token = issue_pass(db, registration)
        if download_token:
            created.append({"id": item.id, "guest_name": guest.full_name, "code": item.code, "download_url": f"{__import__('app.core.config', fromlist=['settings']).settings.FRONTEND_URL.rstrip('/')}/pass-download/{download_token}"})
        else:
            existing += 1
    return {"generated": len(created), "already_issued": existing, "skipped": skipped, "passes": created}


@router.get("/events/{event_id}/passes")
def list_passes(event_id: int, db: SessionDep, membership: Annotated[OrganizationMembership, Depends(get_current_membership)]):
    get_event(db, event_id, membership.organization_id)
    rows = db.exec(select(Pass, EventGuest, Guest).join(EventGuest, Pass.event_guest_id == EventGuest.id).join(Guest, EventGuest.guest_id == Guest.id).where(EventGuest.event_id == event_id).order_by(Pass.created_at.desc())).all()
    return [{"id": p.id, "code": p.code, "status": p.status, "delivery_status": p.delivery_status, "delivered_at": p.delivered_at, "issued_at": p.issued_at, "guest_id": g.id, "guest_name": g.full_name, "email": g.email, "registration_status": eg.registration_status} for p, eg, g in rows]


@router.post("/events/{event_id}/passes/bulk-download")
def bulk_download(event_id: int, db: SessionDep, membership: Annotated[OrganizationMembership, Depends(get_current_membership)], _: Annotated[None, Depends(require_organization_admin)]):
    get_event(db, event_id, membership.organization_id)
    passes = db.exec(select(Pass).join(EventGuest, Pass.event_guest_id == EventGuest.id).where(EventGuest.event_id == event_id, Pass.status == PassStatus.ACTIVE, Pass.qr_token_encrypted.is_not(None))).all()
    if not passes:
        raise HTTPException(status_code=404, detail="No active passes are available")
    archive = make_zip(db, passes)
    return Response(content=archive, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="event-{event_id}-passes.zip"'})


@router.post("/events/{event_id}/passes/send")
def send_event_passes(event_id: int, db: SessionDep, membership: Annotated[OrganizationMembership, Depends(get_current_membership)], _: Annotated[None, Depends(require_organization_admin)]):
    event = get_event(db, event_id, membership.organization_id)
    rows = db.exec(select(Pass, EventGuest, Guest).join(EventGuest, Pass.event_guest_id == EventGuest.id).join(Guest, EventGuest.guest_id == Guest.id).where(EventGuest.event_id == event_id, Pass.status == PassStatus.ACTIVE)).all()
    sent, failed, skipped = 0, 0, 0
    for item, registration, guest in rows:
        if not guest.email or not item.download_token_encrypted:
            skipped += 1; continue
        token = decrypt_qr_token(item.download_token_encrypted)
        url = f"{__import__('app.core.config', fromlist=['settings']).settings.FRONTEND_URL.rstrip('/')}/pass-download/{token}"
        try:
            send_pass_email(guest.email, guest.full_name, event.name, url)
            item.delivery_status = "sent"; item.delivered_at = datetime.now(timezone.utc); db.add(item); db.commit(); sent += 1
        except HTTPException:
            item.delivery_status = "failed"; db.add(item); db.commit(); failed += 1
    return {"sent": sent, "failed": failed, "skipped": skipped}


@router.post("/passes/{pass_id}/resend")
def resend_pass(pass_id: int, db: SessionDep, membership: Annotated[OrganizationMembership, Depends(get_current_membership)], _: Annotated[None, Depends(require_organization_admin)]):
    item = db.get(Pass, pass_id)
    if not item:
        raise HTTPException(status_code=404, detail="Pass not found")
    payload = pass_payload(db, item)
    if payload["event"].organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Pass not found")
    if item.status != PassStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Only active passes can be sent")
    guest = payload["guest"]
    if not guest.email or not item.download_token_encrypted:
        raise HTTPException(status_code=422, detail="Guest has no email address")
    from app.core.config import settings
    token = decrypt_qr_token(item.download_token_encrypted)
    send_pass_email(guest.email, guest.full_name, payload["event"].name, f"{settings.FRONTEND_URL.rstrip('/')}/pass-download/{token}")
    item.delivery_status = "sent"; item.delivered_at = datetime.now(timezone.utc); db.add(item); db.commit()
    return {"message": "Pass email sent"}


@router.post("/passes/{pass_id}/revoke")
def revoke_pass(pass_id: int, db: SessionDep, membership: Annotated[OrganizationMembership, Depends(get_current_membership)], _: Annotated[None, Depends(require_organization_admin)]):
    item = db.get(Pass, pass_id)
    if not item:
        raise HTTPException(status_code=404, detail="Pass not found")
    payload = pass_payload(db, item)
    if payload["event"].organization_id != membership.organization_id:
        raise HTTPException(status_code=404, detail="Pass not found")
    item.status = PassStatus.REVOKED; item.revoked_at = datetime.now(timezone.utc); item.qr_token_encrypted = None; item.download_token_encrypted = None; item.download_token_hash = None
    db.add(item); db.commit()
    return {"message": "Pass revoked"}


@router.get("/public/passes/download/{token}")
def public_download(token: str, db: SessionDep):
    hashed = token_hash(token)
    item = db.exec(select(Pass).where(Pass.download_token_hash == hashed, Pass.status == PassStatus.ACTIVE)).first()
    if not item or not item.download_token_hash or not hmac.compare_digest(item.download_token_hash, hashed):
        raise HTTPException(status_code=404, detail="Pass download link is invalid or has been revoked")
    if item.expires_at:
        expiry = item.expires_at if item.expires_at.tzinfo else item.expires_at.replace(tzinfo=timezone.utc)
        if expiry <= datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="This pass has expired")
    qr_token = decrypt_qr_token(item.qr_token_encrypted)
    pdf = render_pdf(db, item, f"LIINKE:PASS:{qr_token}")
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{item.code}.pdf"', "Cache-Control": "private, no-store"})
