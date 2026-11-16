import json
import unittest

from sqlmodel import Session, SQLModel, create_engine

import app.models
from app.api.v1.endpoints.guests import (
    _map_row,
    _suggest_mappings,
    _validate_mappings,
)
from app.models.event import Event, EventStatus
from app.models.eventCustomField import EventCustomField, EventCustomFieldType
from app.models.guest import Guest, GuestCreate
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
