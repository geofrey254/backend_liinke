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

## Development

Run the development server:

```bash
uvicorn app.main:app --reload
```

## Vision

Liinke is being built to evolve beyond a simple QR-code generator into:

> **Enterprise Event Access & Guest Operations Infrastructure**

The backend will provide the foundation for secure access control, attendee management, workflow automation, and event intelligence.
