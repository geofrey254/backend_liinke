# Liinke Backend

Backend API for **Liinke**, an event access and guest operations platform built with **FastAPI**.

Liinke helps organizations create and manage events, register guests, generate secure event passes, and manage attendee access.

The long-term vision is to provide enterprise-grade infrastructure for **event access, guest management, accreditation, and event operations**.

## Tech Stack

- **Python**
- **FastAPI**
- **PostgreSQL**
- **Redis** _(planned)_
- **Docker** _(planned)_

## Core Features

The backend will support:

- Organization / tenant management
- User authentication and authorization
- Role-based permissions
- Event management
- Guest management
- Bulk guest import via CSV/XLSX
- Event pass generation
- QR code validation
- Access control
- Attendance tracking
- Audit logs
- Event analytics

The product blueprint identifies multi-tenancy, roles, permissions, events, branding, and analytics as core platform capabilities.

## Project Structure

```text
liinke-backend/
├── app/
│   ├── main.py
│   ├── api/
│   ├── core/
│   ├── models/
│   ├── database/
│   ├── services/
│   └── utils/
├── tests/
├── .env.example
├── requirements.txt
├── Dockerfile
└── README.md
```

> The structure can evolve as the backend grows.

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/geofrey254/backend_liinke.git
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:

**macOS / Linux**

```bash
source venv/bin/activate
```

**Windows**

```bash
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/liinke
```

### 5. Run the API

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

FastAPI documentation:

```text
http://localhost:8000/docs
```

## API Direction

The API will gradually be organized around the main Liinke resources:

```text
/auth
/organizations
/users
/events
/guests
/passes
/access
/attendance
/analytics
```

## Guest & Pass Workflow

One of the core Liinke workflows is:

```text
Guest List
    ↓
CSV/XLSX Import
    ↓
Validation
    ↓
Guest Records
    ↓
Pass Generation
    ↓
Pass Distribution
    ↓
Event Check-in
    ↓
Attendance & Analytics
```

The product blueprint specifically identifies CSV/XLSX guest import, validation, bulk pass generation, and automated distribution as a core workflow.

### Guest onboarding API

Guest onboarding is organization-scoped and restricted to organization admins and owners:

- `POST /api/v1/guests` and `PATCH /api/v1/guests/{guest_id}` add or clean one guest.
- `GET /api/v1/guests` lists guests with optional `search`, `limit`, and `offset` filters.
- `POST /api/v1/events/{event_id}/guest-registrations` creates a guest and registers them.
- `POST /api/v1/events/{event_id}/guest-registrations/existing` registers an existing guest.
- `GET /api/v1/events/{event_id}/guest-registrations` lists registrations for an event.
- `GET /api/v1/events/{event_id}/access-levels` lists assignable event access levels.
- `POST /api/v1/events/{event_id}/custom-fields` defines an event-specific registration field.
- `POST /api/v1/guest-imports` accepts `.csv`, `.xlsx`, or `.xlsm` files (up to 10 MB).
- `POST /api/v1/guest-imports/{batch_id}/mapping` maps any source column names to the canonical guest fields.
- `GET /api/v1/guest-imports/{batch_id}/rows` previews parsed rows, including validation errors.
- `PATCH /api/v1/guest-imports/{batch_id}/rows/{row_id}` cleans a row before commit.
- `POST /api/v1/guest-imports/{batch_id}/commit` creates valid guests and marks existing or invalid rows for review.

Spreadsheet headers are matched case-insensitively. Supported aliases include `Name`, `Email Address`, `Phone Number`, `Company`, and `Job Title`; the canonical fields are `full_name`, `email`, `phone`, `organization_name`, and `job_title`.

Uploads first enter `mapping` status and return the source columns, sample rows, and suggested mappings. The client can accept those suggestions or send a custom mapping such as `{"Attendee": "full_name", "Work Email": "email", "Employer": "organization_name"}`. The API validates the mapping, then normalizes and validates every row before allowing commit.

## Development

Run the development server:

```bash
uvicorn app.main:app --reload
```

## Vision

Liinke is being built to evolve beyond a simple QR-code generator into:

> **Enterprise Event Access & Guest Operations Infrastructure**

The backend will provide the foundation for secure access control, attendee management, workflow automation, and event intelligence.

## Team invitations and Resend

The team invitation endpoints are available under the API root:

- `GET /me/invitations` — list invitations for the active organization.
- `POST /me/invitations` — create and email an invitation (`email`, optional `role`).
- `POST /me/invitations/{id}/resend` — rotate the invitation token and resend.
- `DELETE /me/invitations/{id}` — revoke a pending invitation.
- `GET /invitations/lookup?token=...` — read the public invitation details.
- `POST /invitations/accept?token=...` — accept as the authenticated invited user.

Configure these backend environment variables:

```dotenv
RESEND_API_KEY=re_...
RESEND_FROM_EMAIL=Liinke <invites@your-verified-domain.com>
FRONTEND_URL=https://your-frontend-domain.com
# Keep this secret stable; used to encrypt stored pass credentials. If omitted, JWT_SECRET_KEY is used.
PASS_ENCRYPTION_KEY=replace-with-a-long-random-secret
```

Verify the sender domain in Resend before using a production sender address. The
`onboarding@resend.dev` default is intended only for Resend's limited testing
mode. `httpx` is already a project dependency; no additional Resend SDK is
required.

The invitation link opens `/invite/accept?token=...` in the frontend. Run the
Alembic migration that creates `organization_invitations` before deploying this
feature to an existing database.

## Guest passes

Guest passes are managed from the organization's **Passes** workspace in the frontend. The backend adds event-scoped pass templates, unique QR credentials, PDF rendering, private download links, email distribution through Resend, bulk ZIP downloads, and pass revocation.

Install the additional backend dependencies from `requirements.txt`, then apply the schema migration:

```bash
pip install -r requirements.txt
alembic upgrade head
```

Configure `FRONTEND_URL`, `RESEND_API_KEY`, and `RESEND_FROM_EMAIL` for email delivery. Set a stable, random `PASS_ENCRYPTION_KEY` in the backend environment to encrypt QR and download credentials at rest. If it is omitted, the backend derives the encryption key from `JWT_SECRET_KEY`; changing that secret will make previously encrypted pass credentials unreadable.

Eligible guests are registrations in `registered`, `confirmed`, or `approved` state. Passes are generated once per eligible event registration while an active pass exists. The QR payload is `LIINKE:PASS:<credential>`; the credential is hashed for comparison and encrypted at rest so the PDF can be rendered again. Download credentials are separate from QR credentials and can be revoked independently by revoking the pass.

Scanning and entry validation are intentionally not included in this phase.
