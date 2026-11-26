import json
import unittest

from sqlmodel import Session, SQLModel, create_engine, select

import app.models
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from app.api.v1.endpoints.guests import (
    _map_row,
    _parse_csv,
    _persist_import_batch,
    _suggest_mappings,
    _validate_mappings,
)
from app.models.event import Event, EventStatus
from app.models.eventCustomField import EventCustomField, EventCustomFieldType
from app.models.guest import Guest, GuestCreate
from app.models.importBatches import ImportBatch, ImportBatchStatus
from app.models.importRows import ImportRow, ImportRowStatus
from app.services.guest_onboarding_service import (
    find_possible_duplicates,
    normalize_identity,
    validate_custom_fields,
)


class GuestOnboardingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite://")
        SQLModel.metadata.create_all(cls.engine)

    def test_custom_source_columns_are_mapped(self):
        headers = ["Attendee", "Work Email", "Employer"]
        mapping = {
            "Attendee": "full_name",
            "Work Email": "email",
            "Employer": "organization_name",
        }
        _validate_mappings(mapping, headers)
        self.assertEqual(
            _map_row(
                {"Attendee": " Jane Doe ", "Work Email": "jane@example.com", "Employer": "Acme"},
                mapping,
            ),
            {
                "full_name": "Jane Doe",
                "email": "jane@example.com",
                "organization_name": "Acme",
            },
        )


    def test_access_level_is_suggested_and_can_be_mapped(self):
        headers = ["Full Name", "Access Level"]
        mapping = _suggest_mappings(headers)
        self.assertEqual(mapping["Access Level"], "access_level")
        _validate_mappings(mapping, headers)
        self.assertEqual(
            _map_row({"Full Name": "Jane Doe", "Access Level": "VIP"}, mapping),
            {"full_name": "Jane Doe", "access_level": "VIP"},
        )

    def test_csv_parser_detects_semicolon_delimiter(self):
        headers, rows = _parse_csv(
            "Full Name;Email;Access Level\nJane Doe;jane@example.com;VIP\n".encode("utf-8")
        )
        self.assertEqual(headers, ["Full Name", "Email", "Access Level"])
        self.assertEqual(rows[0]["Access Level"], "VIP")


    def test_same_organization_can_import_same_filename_multiple_times(self):
        with Session(self.engine) as db:
            first = ImportBatch(
                organization_id=1,
                event_id=13,
                uploaded_by_id=6,
                original_file_name="guests.xlsx",
                file_storage_key="inline/first",
                file_type="xlsx",
                total_rows=1,
                status=ImportBatchStatus.MAPPING,
            )
            second = ImportBatch(
                organization_id=1,
                event_id=14,
                uploaded_by_id=6,
                original_file_name="guests.xlsx",
                file_storage_key="inline/second",
                file_type="xlsx",
                total_rows=1,
                status=ImportBatchStatus.MAPPING,
            )

            _persist_import_batch(db, first, [{"Full Name": "Jane Doe"}])
            _persist_import_batch(db, second, [{"Full Name": "John Doe"}])

            saved = db.exec(
                select(ImportBatch).where(
                    ImportBatch.organization_id == 1,
                    ImportBatch.original_file_name == "guests.xlsx",
                )
            ).all()
            self.assertEqual(2, len(saved))
            self.assertEqual({13, 14}, {batch.event_id for batch in saved})

    def test_import_batch_integrity_error_rolls_back_transaction(self):
        with Session(self.engine) as db:
            existing = ImportBatch(
                id=98765,
                organization_id=1,
                event_id=13,
                uploaded_by_id=6,
                original_file_name="existing.xlsx",
                file_storage_key="inline/existing",
                file_type="xlsx",
                total_rows=1,
                status=ImportBatchStatus.MAPPING,
            )
            db.add(existing)
            db.commit()

            conflicting = ImportBatch(
                id=98765,
                organization_id=1,
                event_id=14,
                uploaded_by_id=6,
                original_file_name="another.xlsx",
                file_storage_key="inline/conflicting",
                file_type="xlsx",
                total_rows=1,
                status=ImportBatchStatus.MAPPING,
            )
            with self.assertRaises(HTTPException) as raised:
                _persist_import_batch(db, conflicting, [{"Full Name": "Should Roll Back"}])

            self.assertEqual(409, raised.exception.status_code)
            self.assertEqual(1, len(db.exec(select(ImportBatch)).all()))
            self.assertEqual(0, len(db.exec(select(ImportRow)).all()))

    def test_mapping_requires_identity_fields(self):
        with self.assertRaises(Exception):
            _validate_mappings({"Mail": "email"}, ["Attendee", "Mail"])

    def test_duplicate_detection_is_case_and_whitespace_insensitive(self):
        with Session(self.engine) as db:
            guest = Guest(
                organization_id=1,
                full_name="Jane Doe",
                email="Jane@example.com",
                phone="+254 700 000 000",
            )
            db.add(guest)
            db.commit()
            matches = find_possible_duplicates(
                db,
                1,
                GuestCreate(
                    full_name="  jane   doe ",
                    email="other@example.com",
                    phone="+254 700 000 000",
                ),
            )
            self.assertEqual([guest.id], [match.id for match in matches])
            self.assertEqual("jane doe", normalize_identity(" Jane   Doe "))

    def test_custom_field_values_are_validated_for_event(self):
        with Session(self.engine) as db:
            event = Event(
                organization_id=2,
                name="Conference",
                slug="conference-custom-fields",
                status=EventStatus.DRAFT,
            )
            db.add(event)
            db.flush()
            db.add(
                EventCustomField(
                    event_id=event.id,
                    field_key="diet",
                    label="Diet",
                    field_type=EventCustomFieldType.DROPDOWN,
                    required=True,
                    options=json.dumps(["none", "vegetarian"]),
                )
            )
            db.commit()
            validate_custom_fields(db, event.id, {"diet": "vegetarian"})
            with self.assertRaises(Exception):
                validate_custom_fields(db, event.id, {"diet": "halal"})


if __name__ == "__main__":
    unittest.main()
