import csv
import io
import json
import re
from datetime import datetime, timezone
from typing import Annotated, Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, ValidationError, Field as PydanticField
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.core.dependencies import (
    get_current_user,
    get_current_membership,
    require_organization_admin,
)
from app.database.session import SessionDep
from app.models.guest import Guest, GuestCreate, GuestResponse, GuestUpdate
from app.models.event import Event
from app.models.eventAccessLevel import EventAccessLevel
from app.models.eventGuest import EventGuest, EventGuestResponse, EventGuestStatus
from app.models.eventCustomField import (
    EventCustomField,
    EventCustomFieldCreate,
    EventCustomFieldResponse,
)
from app.models.importBatches import (
    ImportBatch,
    ImportBatchResponse,
    ImportBatchStatus,
)
from app.models.importRows import ImportRow, ImportRowResponse, ImportRowStatus
from app.models.organizationMembership import OrganizationMembership
from app.models.user import User
from app.services.guest_onboarding_service import (
    find_possible_duplicates,
    get_event_for_org,
    register_guest,
    validate_custom_fields,
    validate_access_level,
)

try:
    from openpyxl import load_workbook
except ImportError:  # pragma: no cover - dependency is declared in requirements.txt
    load_workbook = None


router = APIRouter()
MAX_IMPORT_SIZE = 10 * 1024 * 1024
HEADER_ALIASES = {
    "name": "full_name",
    "fullname": "full_name",
    "guestname": "full_name",
    "emailaddress": "email",
    "mail": "email",
    "phonenumber": "phone",
    "company": "organization_name",
    "organization": "organization_name",
    "jobtitle": "job_title",
    "accesslevel": "access_level",
    "access": "access_level",
    "ticket": "access_level",
    "tickettype": "access_level",
    "passtype": "access_level",
    "pass": "access_level",
}
GUEST_FIELDS = {"full_name", "first_name", "last_name", "email", "phone", "organization_name", "job_title"}
IMPORT_FIELDS = GUEST_FIELDS | {"access_level"}
SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xlsm"}


def _normalize_header(value: Any) -> str:
    key = re.sub(r"[^a-z0-9]", "", str(value or "").lower())
    return HEADER_ALIASES.get(key, key)


def _clean_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_csv(content: bytes) -> tuple[list[str], list[dict[str, Any]]]:
    # Excel exports may be UTF-8 (with or without BOM), UTF-16, or Windows-1252.
    text = None
    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise HTTPException(status_code=422, detail="The CSV encoding is not supported")
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise HTTPException(status_code=422, detail="The spreadsheet has no header row")
    headers = [str(header).strip() for header in reader.fieldnames]
    return headers, [
        {str(key).strip(): _clean_value(value) for key, value in row.items() if key}
        for row in reader
        if any(value not in (None, "") for value in row.values())
    ]


def _parse_excel(content: bytes) -> tuple[list[str], list[dict[str, Any]]]:
    if load_workbook is None:
        raise HTTPException(status_code=500, detail="Excel import support is not installed; install the backend requirements")
    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        worksheet = workbook.active
        rows = worksheet.iter_rows(values_only=True)
        headers = next(rows, None)
        if not headers or not any(header is not None for header in headers):
            raise HTTPException(status_code=422, detail="The spreadsheet has no header row")
        source_headers = [str(header).strip() if header is not None else "" for header in headers]
        parsed = [
            {key: _clean_value(value) for key, value in zip(source_headers, values, strict=False) if key}
            for values in rows
        ]
        return source_headers, [row for row in parsed if any(value is not None for value in row.values())]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Unable to read this Excel file. Ensure it is a valid .xlsx or .xlsm workbook.") from exc
    finally:
        if "workbook" in locals():
            workbook.close()


def _parse_file(
    filename: str,
    content: bytes,
) -> tuple[str, list[str], list[dict[str, Any]]]:
    extension = "." + filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Only CSV, XLSX, and XLSM files are supported")
    if extension == ".csv":
        headers, rows = _parse_csv(content)
        return "csv", headers, rows
    headers, rows = _parse_excel(content)
    return "xlsx", headers, rows


def _suggest_mappings(headers: list[str]) -> dict[str, str]:
    suggestions: dict[str, str] = {}
    for header in headers:
        target = _normalize_header(header)
        if target in IMPORT_FIELDS and target not in suggestions.values():
            suggestions[header] = target
    return suggestions


class GuestImportMapping(BaseModel):
    mappings: dict[str, str]
    default_access_level_id: int | None = PydanticField(default=None, gt=0)


class EventGuestCreate(BaseModel):
    guest_id: int
    access_level_id: int | None = None
    custom_field_values: dict[str, Any] | None = None
    registration_status: EventGuestStatus = EventGuestStatus.REGISTERED


class EventGuestUpdate(BaseModel):
    access_level_id: int | None = None
    custom_field_values: dict[str, Any] | None = None
    registration_status: EventGuestStatus | None = None


class ImportDuplicateResolution(BaseModel):
    action: Literal["use_existing", "create_new", "skip"]
    guest_id: int | None = None


class GuestRegistrationCreate(GuestCreate):
    event_id: int
    access_level_id: int | None = None
    custom_field_values: dict[str, Any] | None = None
    registration_status: EventGuestStatus = EventGuestStatus.REGISTERED


class GuestImportMappingResponse(ImportBatchResponse):
    source_columns: list[str]
    suggested_mappings: dict[str, str]
    sample_rows: list[dict[str, Any]]


def _source_columns(batch: ImportBatch, db: SessionDep) -> list[str]:
    first_row = db.exec(
        select(ImportRow)
        .where(ImportRow.import_batch_id == batch.id)
        .order_by(ImportRow.row_number)
    ).first()
    if first_row is None:
        return []
    return list(json.loads(first_row.raw_data).keys())


def _map_row(
    raw: dict[str, Any],
    mappings: dict[str, str],
) -> dict[str, Any]:
    return {
        target: _clean_value(raw.get(source))
        for source, target in mappings.items()
        if target in IMPORT_FIELDS
    }


def _validate_mappings(
    mappings: dict[str, str],
    source_columns: list[str],
) -> None:
    unknown_sources = set(mappings) - set(source_columns)
    if unknown_sources:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown source columns: {', '.join(sorted(unknown_sources))}",
        )
    invalid_targets = set(mappings.values()) - IMPORT_FIELDS
    if invalid_targets:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported guest fields: {', '.join(sorted(invalid_targets))}",
        )
    targets = list(mappings.values())
    if len(targets) != len(set(targets)):
        raise HTTPException(status_code=422, detail="Each guest field can only be mapped once")
    if "full_name" not in targets and not {"first_name", "last_name"} <= set(targets):
        raise HTTPException(
            status_code=422,
            detail="Map full_name or both first_name and last_name",
        )


def _batch_mapping_response(batch: ImportBatch, db: SessionDep) -> GuestImportMappingResponse:
    columns = _source_columns(batch, db)
    return GuestImportMappingResponse(
        **batch.model_dump(),
        source_columns=columns,
        suggested_mappings=_suggest_mappings(columns),
        sample_rows=[
            json.loads(row.raw_data)
            for row in db.exec(
                select(ImportRow)
                .where(ImportRow.import_batch_id == batch.id)
                .order_by(ImportRow.row_number)
                .limit(5)
            ).all()
        ],
    )


def _custom_field_response(field: EventCustomField) -> dict[str, Any]:
    return {
        "id": field.id,
        "event_id": field.event_id,
        "field_key": field.field_key,
        "label": field.label,
        "field_type": field.field_type,
        "required": field.required,
        "options": json.loads(field.options) if field.options else None,
        "is_active": field.is_active,
    }


def _row_validation(row: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    data = {
        "full_name": row.get("full_name"),
        "email": row.get("email"),
        "phone": row.get("phone"),
        "organization_name": row.get("organization_name"),
        "job_title": row.get("job_title"),
    }
    try:
        guest = GuestCreate.model_validate(data)
    except ValidationError as exc:
        return None, [
            f"{error['loc'][0]}: {error['msg']}" for error in exc.errors()
        ]
    normalized = guest.model_dump(mode="json")
    if row.get("access_level") is not None:
        normalized["access_level"] = row["access_level"]
    return normalized, []


def _batch_for_org(db: SessionDep, batch_id: int, organization_id: int) -> ImportBatch:
    batch = db.exec(
        select(ImportBatch).where(
            ImportBatch.id == batch_id,
            ImportBatch.organization_id == organization_id,
        )
    ).first()
    if batch is None:
        raise HTTPException(status_code=404, detail="Import batch not found")
    return batch


def _persist_import_batch(
    db: SessionDep,
    batch: ImportBatch,
    parsed_rows: list[dict[str, Any]],
) -> ImportBatch:
    """Persist an import batch and its rows atomically.

    A failed flush or commit leaves the SQLAlchemy session in a failed state,
    so always roll it back before returning a controlled API error.
    """
    try:
        db.add(batch)
        db.flush()
        for row_number, raw in enumerate(parsed_rows, start=2):
            db.add(
                ImportRow(
                    import_batch_id=batch.id,
                    row_number=row_number,
                    raw_data=json.dumps(raw, default=str),
                    status=ImportRowStatus.PENDING,
                )
            )
        db.commit()
        db.refresh(batch)
        return batch
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The import could not be saved because it conflicts with an "
                "existing database record. Please retry the upload."
            ),
        ) from None


def _refresh_batch_counts(db: SessionDep, batch: ImportBatch) -> None:
    rows = db.exec(select(ImportRow).where(ImportRow.import_batch_id == batch.id)).all()
    batch.total_rows = len(rows)
    batch.valid_rows = sum(
        row.status in {ImportRowStatus.VALIDATED, ImportRowStatus.PROCESSED}
        for row in rows
    )
    batch.invalid_rows = sum(row.status == ImportRowStatus.INVALID for row in rows)
    batch.duplicate_rows = sum(
        row.status == ImportRowStatus.INVALID and row.errors and "duplicate" in row.errors
        for row in rows
    )


@router.post("/guests", response_model=GuestResponse, status_code=status.HTTP_201_CREATED)
def create_guest(
    guest_data: GuestCreate,
    db: SessionDep,
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    _: Annotated[None, Depends(require_organization_admin)],
) -> Guest:
    guest = Guest(
        **guest_data.model_dump(),
        organization_id=membership.organization_id,
    )
    db.add(guest)
    try:
        db.commit()
        db.refresh(guest)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A guest with this email already exists") from None
    return guest


@router.post(
    "/events/{event_id}/guest-registrations",
    response_model=EventGuestResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_new_guest(
    event_id: int,
    registration_data: GuestRegistrationCreate,
    db: SessionDep,
    current_user: Annotated[User, Depends(get_current_user)],
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    _: Annotated[None, Depends(require_organization_admin)],
) -> EventGuest:
    if registration_data.event_id != event_id:
        raise HTTPException(status_code=422, detail="Event IDs do not match")
    get_event_for_org(db, event_id, membership.organization_id)
    guest_data = GuestCreate.model_validate(
        registration_data.model_dump(
            exclude={"event_id", "access_level_id", "custom_field_values", "registration_status"}
        )
    )
    duplicates = find_possible_duplicates(db, membership.organization_id, guest_data)
    if duplicates:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "A possible matching guest already exists",
                "guest_ids": [guest.id for guest in duplicates],
            },
        )
    guest = Guest(**guest_data.model_dump(), organization_id=membership.organization_id)
    db.add(guest)
    db.flush()
    registration = register_guest(
        db,
        membership.organization_id,
        current_user.id,
        event_id,
        guest.id,
        registration_data.access_level_id,
        registration_data.custom_field_values,
        registration_data.registration_status,
    )
    db.commit()
    db.refresh(registration)
    return registration


@router.post(
    "/events/{event_id}/guest-registrations/existing",
    response_model=EventGuestResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_existing_guest(
    event_id: int,
    registration_data: EventGuestCreate,
    db: SessionDep,
    current_user: Annotated[User, Depends(get_current_user)],
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    _: Annotated[None, Depends(require_organization_admin)],
) -> EventGuest:
    registration = register_guest(
        db,
        membership.organization_id,
        current_user.id,
        event_id,
        registration_data.guest_id,
        registration_data.access_level_id,
        registration_data.custom_field_values,
        registration_data.registration_status,
    )
    db.commit()
    db.refresh(registration)
    return registration


@router.get(
    "/events/{event_id}/guest-registrations",
    response_model=list[EventGuestResponse],
)
def list_event_guests(
    event_id: int,
    db: SessionDep,
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    _: Annotated[None, Depends(require_organization_admin)],
) -> list[EventGuest]:
    get_event_for_org(db, event_id, membership.organization_id)
    return db.exec(
        select(EventGuest).where(EventGuest.event_id == event_id)
    ).all()

@router.post(
    "/events/{event_id}/custom-fields",
    response_model=EventCustomFieldResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_event_custom_field(
    event_id: int,
    field_data: EventCustomFieldCreate,
    db: SessionDep,
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    _: Annotated[None, Depends(require_organization_admin)],
) -> dict[str, Any]:
    get_event_for_org(db, event_id, membership.organization_id)
    field = EventCustomField(
        event_id=event_id,
        field_key=field_data.field_key,
        label=field_data.label,
        field_type=field_data.field_type,
        required=field_data.required,
        options=json.dumps(field_data.options) if field_data.options else None,
    )
    db.add(field)
    try:
        db.commit()
        db.refresh(field)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A custom field with this key already exists") from None
    return _custom_field_response(field)


@router.get(
    "/events/{event_id}/custom-fields",
    response_model=list[EventCustomFieldResponse],
)
def list_event_custom_fields(
    event_id: int,
    db: SessionDep,
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    _: Annotated[None, Depends(require_organization_admin)],
) -> list[dict[str, Any]]:
    get_event_for_org(db, event_id, membership.organization_id)
    fields = db.exec(
        select(EventCustomField).where(EventCustomField.event_id == event_id)
    ).all()
    return [_custom_field_response(field) for field in fields]


@router.patch(
    "/events/{event_id}/guest-registrations/{registration_id}",
    response_model=EventGuestResponse,
)
def update_event_guest(
    event_id: int,
    registration_id: int,
    registration_data: EventGuestUpdate,
    db: SessionDep,
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    _: Annotated[None, Depends(require_organization_admin)],
) -> EventGuest:
    get_event_for_org(db, event_id, membership.organization_id)
    registration = db.exec(
        select(EventGuest).join(Guest).where(
            EventGuest.id == registration_id,
            EventGuest.event_id == event_id,
            Guest.organization_id == membership.organization_id,
        )
    ).first()
    if registration is None:
        raise HTTPException(status_code=404, detail="Event guest registration not found")
    if "access_level_id" in registration_data.model_fields_set:
        validate_access_level(db, event_id, registration_data.access_level_id)
        registration.access_level_id = registration_data.access_level_id
    if registration_data.registration_status is not None:
        allowed = {
            EventGuestStatus.DRAFT: {EventGuestStatus.PENDING_APPROVAL, EventGuestStatus.CANCELLED},
            EventGuestStatus.PENDING_APPROVAL: {EventGuestStatus.APPROVED, EventGuestStatus.DECLINED, EventGuestStatus.CANCELLED},
            EventGuestStatus.APPROVED: {EventGuestStatus.INVITED, EventGuestStatus.CANCELLED},
            EventGuestStatus.INVITED: {EventGuestStatus.CONFIRMED, EventGuestStatus.CANCELLED},
            EventGuestStatus.REGISTERED: {EventGuestStatus.CONFIRMED, EventGuestStatus.CANCELLED},
            EventGuestStatus.CONFIRMED: {EventGuestStatus.CHECKED_IN, EventGuestStatus.CANCELLED},
            EventGuestStatus.CHECKED_IN: set(),
            EventGuestStatus.DECLINED: set(),
            EventGuestStatus.CANCELLED: set(),
        }
        if registration_data.registration_status != registration.registration_status and registration_data.registration_status not in allowed.get(registration.registration_status, set()):
            raise HTTPException(status_code=409, detail="Invalid registration status transition")
        registration.registration_status = registration_data.registration_status
        if registration.registration_status == EventGuestStatus.APPROVED:
            registration.approved_at = datetime.now(timezone.utc)
    registration.custom_field_values = (
        json.dumps(registration_data.custom_field_values)
        if registration_data.custom_field_values is not None else registration.custom_field_values
    )
    if registration_data.custom_field_values is not None:
        validate_custom_fields(db, event_id, registration_data.custom_field_values)
    db.add(registration)
    db.commit()
    db.refresh(registration)
    return registration


@router.get("/guests", response_model=list[GuestResponse])
def list_guests(
    db: SessionDep,
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    _: Annotated[None, Depends(require_organization_admin)],
    search: str | None = Query(default=None, min_length=1),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Guest]:
    statement = select(Guest).where(Guest.organization_id == membership.organization_id)
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(
            (Guest.full_name.ilike(pattern))
            | (Guest.email.ilike(pattern))
            | (Guest.organization_name.ilike(pattern))
        )
    return db.exec(statement.offset(offset).limit(limit)).all()


@router.get("/guests/{guest_id}", response_model=GuestResponse)
def get_guest(
    guest_id: int,
    db: SessionDep,
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    _: Annotated[None, Depends(require_organization_admin)],
) -> Guest:
    guest = db.exec(
        select(Guest).where(
            Guest.id == guest_id,
            Guest.organization_id == membership.organization_id,
        )
    ).first()
    if guest is None:
        raise HTTPException(status_code=404, detail="Guest not found")
    return guest


@router.patch("/guests/{guest_id}", response_model=GuestResponse)
def update_guest(
    guest_id: int,
    guest_data: GuestUpdate,
    db: SessionDep,
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    _: Annotated[None, Depends(require_organization_admin)],
) -> Guest:
    guest = get_guest(guest_id, db, membership, None)
    updates = guest_data.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="No guest fields provided for update")
    guest.sqlmodel_update(updates)
    try:
        db.add(guest)
        db.commit()
        db.refresh(guest)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A guest with this email already exists") from None
    return guest


@router.delete("/guests/{guest_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_guest(
    guest_id: int,
    db: SessionDep,
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    _: Annotated[None, Depends(require_organization_admin)],
) -> None:
    guest = get_guest(guest_id, db, membership, None)
    db.delete(guest)
    db.commit()


@router.post(
    "/guest-imports",
    response_model=GuestImportMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_guest_import(
    file: Annotated[UploadFile, File()],
    db: SessionDep,
    current_user: Annotated[User, Depends(get_current_user)],
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    _: Annotated[None, Depends(require_organization_admin)],
    event_id: int = Query(..., description="Event that imported guests will be registered for"),
) -> ImportBatch:
    get_event_for_org(db, event_id, membership.organization_id)
    content = file.file.read(MAX_IMPORT_SIZE + 1)
    if len(content) > MAX_IMPORT_SIZE:
        raise HTTPException(status_code=413, detail="Import files must be 10 MB or smaller")
    file_type, source_columns, parsed_rows = _parse_file(file.filename or "", content)
    if not parsed_rows:
        raise HTTPException(status_code=422, detail="The spreadsheet contains no guest rows")
    batch = ImportBatch(
        organization_id=membership.organization_id,
        event_id=event_id,
        uploaded_by_id=current_user.id,
        original_file_name=file.filename or "guest-import",
        file_storage_key=f"inline/{uuid4()}",
        file_type=file_type,
        total_rows=len(parsed_rows),
        status=ImportBatchStatus.MAPPING,
        column_mappings=json.dumps({"suggested": _suggest_mappings(source_columns)}),
    )
    batch = _persist_import_batch(db, batch, parsed_rows)
    return _batch_mapping_response(batch, db)


@router.post(
    "/guest-imports/{batch_id}/mapping",
    response_model=ImportBatchResponse,
)
def map_guest_import(
    batch_id: int,
    mapping: GuestImportMapping,
    db: SessionDep,
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    _: Annotated[None, Depends(require_organization_admin)],
) -> ImportBatch:
    batch = _batch_for_org(db, batch_id, membership.organization_id)
    if batch.event_id is None:
        raise HTTPException(status_code=422, detail="Import batch is not linked to an event")
    if batch.status not in {ImportBatchStatus.MAPPING, ImportBatchStatus.READY_FOR_REVIEW}:
        raise HTTPException(status_code=409, detail="This import is no longer awaiting mapping")
    source_columns = _source_columns(batch, db)
    _validate_mappings(mapping.mappings, source_columns)
    if "access_level" not in mapping.mappings.values() and mapping.default_access_level_id is None:
        raise HTTPException(
            status_code=422,
            detail="Map an access_level column or select a default access level for this import",
        )
    default_access_level = None
    if mapping.default_access_level_id is not None:
        default_access_level = validate_access_level(db, batch.event_id, mapping.default_access_level_id)
    active_levels = db.exec(
        select(EventAccessLevel).where(
            EventAccessLevel.event_id == batch.event_id,
            EventAccessLevel.is_active.is_(True),
        )
    ).all()
    levels_by_value = {}
    for level in active_levels:
        levels_by_value[level.code.strip().casefold()] = level
        levels_by_value[level.name.strip().casefold()] = level
        levels_by_value[str(level.id)] = level
    rows = db.exec(
        select(ImportRow)
        .where(ImportRow.import_batch_id == batch.id)
        .order_by(ImportRow.row_number)
    ).all()
    seen_emails: set[str] = set()
    for row in rows:
        normalized, errors = _row_validation(
            _map_row(json.loads(row.raw_data), mapping.mappings)
        )
        if not errors:
            access_value = normalized.get("access_level")
            access_level = (
                levels_by_value.get(str(access_value).strip().casefold())
                if access_value is not None
                else default_access_level
            )
            if access_level is None:
                errors.append("access_level: provide a valid access level or select a default")
            else:
                normalized["access_level_id"] = access_level.id
            normalized.pop("access_level", None)
        email = str((normalized or {}).get("email") or "").strip().casefold()
        if not errors and email and email in seen_emails:
            errors.append("email: duplicate email in import")
        if not errors and email:
            seen_emails.add(email)
        row.normalized_data = json.dumps(normalized) if normalized else None
        if not errors and normalized:
            possible = find_possible_duplicates(
                db,
                batch.organization_id,
                GuestCreate.model_validate(normalized),
            )
            row.warnings = (
                json.dumps({"possible_guest_ids": [guest.id for guest in possible]})
                if possible else None
            )
        else:
            row.warnings = None
        row.status = ImportRowStatus.VALIDATED if not errors else ImportRowStatus.INVALID
        row.errors = json.dumps(errors) if errors else None
        db.add(row)
    batch.column_mappings = json.dumps({"mappings": mapping.mappings, "default_access_level_id": mapping.default_access_level_id})
    batch.status = ImportBatchStatus.READY_FOR_REVIEW
    _refresh_batch_counts(db, batch)
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


@router.get("/guest-imports/{batch_id}", response_model=GuestImportMappingResponse)
def get_guest_import(
    batch_id: int,
    db: SessionDep,
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    _: Annotated[None, Depends(require_organization_admin)],
) -> GuestImportMappingResponse:
    batch = _batch_for_org(db, batch_id, membership.organization_id)
    return _batch_mapping_response(batch, db)


@router.get("/guest-imports/{batch_id}/rows", response_model=list[ImportRowResponse])
def list_guest_import_rows(
    batch_id: int,
    db: SessionDep,
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    _: Annotated[None, Depends(require_organization_admin)],
    row_status: ImportRowStatus | None = Query(default=None, alias="status"),
) -> list[ImportRow]:
    _batch_for_org(db, batch_id, membership.organization_id)
    statement = select(ImportRow).where(ImportRow.import_batch_id == batch_id)
    if row_status:
        statement = statement.where(ImportRow.status == row_status)
    return db.exec(statement.order_by(ImportRow.row_number)).all()


@router.patch("/guest-imports/{batch_id}/rows/{row_id}", response_model=ImportRowResponse)
def clean_guest_import_row(
    batch_id: int,
    row_id: int,
    data: dict[str, Any],
    db: SessionDep,
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    _: Annotated[None, Depends(require_organization_admin)],
) -> ImportRow:
    _batch_for_org(db, batch_id, membership.organization_id)
    row = db.exec(
        select(ImportRow).where(
            ImportRow.id == row_id,
            ImportRow.import_batch_id == batch_id,
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Import row not found")
    normalized, errors = _row_validation(data)
    previous = json.loads(row.normalized_data or "{}")
    if normalized is not None and previous.get("access_level_id") is not None:
        normalized["access_level_id"] = previous["access_level_id"]
    row.normalized_data = json.dumps(normalized) if normalized else None
    row.errors = json.dumps(errors) if errors else None
    row.status = ImportRowStatus.VALIDATED if not errors else ImportRowStatus.INVALID
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post(
    "/guest-imports/{batch_id}/rows/{row_id}/resolve",
    response_model=ImportRowResponse,
)
def resolve_guest_import_duplicate(
    batch_id: int,
    row_id: int,
    resolution: ImportDuplicateResolution,
    db: SessionDep,
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    _: Annotated[None, Depends(require_organization_admin)],
) -> ImportRow:
    _batch_for_org(db, batch_id, membership.organization_id)
    row = db.exec(
        select(ImportRow).where(
            ImportRow.id == row_id,
            ImportRow.import_batch_id == batch_id,
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Import row not found")
    data = json.loads(row.normalized_data or "{}")
    if resolution.action == "use_existing":
        if resolution.guest_id is None:
            raise HTTPException(status_code=422, detail="guest_id is required")
        guest = db.exec(
            select(Guest).where(
                Guest.id == resolution.guest_id,
                Guest.organization_id == membership.organization_id,
            )
        ).first()
        if guest is None:
            raise HTTPException(status_code=404, detail="Guest not found")
        data["_resolution_guest_id"] = guest.id
        row.status = ImportRowStatus.VALIDATED
    elif resolution.action == "create_new":
        data["_resolution_create_new"] = True
        row.status = ImportRowStatus.VALIDATED
    else:
        row.status = ImportRowStatus.INVALID
        row.errors = json.dumps(["duplicate: skipped by reviewer"])
    row.normalized_data = json.dumps(data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("/guest-imports/{batch_id}/commit", response_model=ImportBatchResponse)
def commit_guest_import(
    batch_id: int,
    db: SessionDep,
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    _: Annotated[None, Depends(require_organization_admin)],
) -> ImportBatch:
    batch = _batch_for_org(db, batch_id, membership.organization_id)
    if batch.event_id is None:
        raise HTTPException(status_code=422, detail="Import batch is not linked to an event")
    if batch.status != ImportBatchStatus.READY_FOR_REVIEW:
        raise HTTPException(
            status_code=409,
            detail="Map and review the import before committing it",
        )
    rows = db.exec(
        select(ImportRow).where(
            ImportRow.import_batch_id == batch.id,
            ImportRow.status == ImportRowStatus.VALIDATED,
        )
    ).all()
    processed_registrations = 0
    for row in rows:
        data = json.loads(row.normalized_data or "{}")
        access_level_id = data.pop("access_level_id", None)
        resolved_guest_id = data.pop("_resolution_guest_id", None)
        create_new = data.pop("_resolution_create_new", False)
        guest_data = GuestCreate.model_validate(data)
        matches = find_possible_duplicates(db, membership.organization_id, guest_data)
        guest = db.get(Guest, resolved_guest_id) if resolved_guest_id else None
        if guest is None and not create_new:
            guest = next(
                (candidate for candidate in matches
                 if guest_data.email and candidate.email
                 and candidate.email.casefold() == guest_data.email.casefold()),
                None,
            )
        if guest is None and matches and not create_new:
            row.status = ImportRowStatus.INVALID
            row.errors = json.dumps(["duplicate: resolve this possible match before commit"])
            continue
        if guest is None:
            guest = Guest(**guest_data.model_dump(), organization_id=membership.organization_id)
            db.add(guest)
            db.flush()
        row.matched_guest_id = guest.id
        registration = register_guest(
            db,
            membership.organization_id,
            batch.uploaded_by_id,
            batch.event_id,
            guest.id,
            access_level_id,
        )
        row.created_event_guest_id = registration.id
        row.status = ImportRowStatus.PROCESSED
        processed_registrations += 1
    batch.status = (
        ImportBatchStatus.COMPLETED
        if processed_registrations == batch.total_rows
        else ImportBatchStatus.PARTIALLY_COMPLETED
    )
    _refresh_batch_counts(db, batch)
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch
