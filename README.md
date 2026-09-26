# WhatsApp Business Enquiry Router

A full-stack WhatsApp Cloud API enquiry router with:
- Django REST API backend
- PostgreSQL database
- Celery workers and Redis
- React frontend dashboard
- React Native mobile application (`app/`)
- Docker Compose setup for local development

## Stack
- Backend: Python 3.12 + Django 5 + DRF + PostgreSQL + Celery
- Frontend: React + Vite
- Messaging: Meta WhatsApp Cloud API, Flows, webhooks and templates
- Infra: Docker Compose (local); AWS ECS/RDS/ElastiCache is the production target

## Routing lifecycle

1. Meta sends a signed event to `POST /api/whatsapp/webhook/`.
2. Django verifies `X-Hub-Signature-256` and immediately queues the payload.
3. A Celery worker parses the message or WhatsApp Flow response and deduplicates it by `wamid`.
4. The customer, enquiry and incoming audit message are stored in PostgreSQL.
5. The selected department resolves to every active department member.
6. One approved `new_department_enquiry` template is sent to each member.
7. Later Meta status events update sent, delivered, read and failed audit records.

## Project structure

- Backend/
- Frontend/
- app/ (Expo React Native application and Android/iOS build automation)
- docker-compose.yml

## Run locally

```bash
docker compose up --build
```

## Deployment script

The deployment helper supports the complete stack or individual application layers:

```bash
./deploy.sh all        # PostgreSQL + Redis + backend + worker + frontend
./deploy.sh frontend   # Frontend container only
./deploy.sh backend    # Backend + worker + PostgreSQL + Redis
./deploy.sh database   # PostgreSQL only
```

The relevant service `.env` file must exist before deployment. The frontend-only command intentionally uses
`--no-deps`; its configured API endpoint must therefore point to an already running backend.

When port 9090 is exposed directly over HTTP, set `SECURE_SSL_REDIRECT=False`. Set it to `True` only when the
backend is behind an HTTPS reverse proxy or load balancer that sends `X-Forwarded-Proto: https`.

Mobile development and Android/iOS build instructions are in `app/README.md`. The mobile app authenticates
against the same Django users and JWT endpoints as the web application; it does not maintain a second password store.

Then access:
- Frontend: http://localhost
- Backend API: http://localhost:9090/api/health/
- Django Admin: http://localhost:9090/admin/

Run validation with:

```bash
docker compose run --rm whatsapp-backend-service python manage.py test
docker compose run --rm whatsapp-backend-service python manage.py check --deploy
```

## Environment files

Each stack has its own .env file for secrets and configuration.
- Backend/.env
- Frontend/.env

Copy `Backend/.env.example` for infrastructure settings. After migrating, open Django Admin and edit
**WhatsApp configuration** before accepting real traffic. This database record stores the business number,
default team, phone-number ID, business-account ID, webhook verification token, webhook signing secret,
Meta access token, and employee-notification template settings. Changes are used by Celery without restarting.
The access token is never copied into notification request/response audit records.

The matching environment variables remain available as initial/fallback configuration, but account-specific
database settings managed through Django Admin take precedence.

The webhook callback URL is `https://<host>/api/whatsapp/webhook/`. Configure Meta to subscribe to
message events. Populate Sales, Support and HR recipients through Django Admin. Flow response field names
supported by the parser are `full_name` (or `name`), `organization_name` (or `organization`), `email`,
`category`, and `message`.

Restrict Django Admin access and encrypt/protect database backups because the access token and webhook secrets
are stored in the database. They are masked in the admin form and are not exposed through the frontend API.

For the first deployment, configure `PLATFORM_ADMIN_EMAIL`, `PLATFORM_ADMIN_PASSWORD`, and optionally
`PLATFORM_ADMIN_USERNAME` in `Backend/.env`. Startup creates the account only when it does not already exist;
the password is hashed by Django and authentication always occurs through `/api/auth/login/`. Credentials are
never embedded or prefilled in the frontend.

## Notes

The legacy campaigns UI and keyword rules remain available for backward compatibility. Structured Flow category
selection is preferred. The `Lead` model is retained as a dashboard projection while `Customer`, `Enquiry`,
`WhatsAppMessage`, and `Notification` are the authoritative routing and audit records.

## Regional user access and deletion

In Identity & access management, choose **India only**, **US only**, or **India and US**
when inviting a user or editing their access, then click **Save access**. Login uses
these saved permissions to show only the configured, active business numbers available
to the user. India matches `+91` and US matches `+1`. API requests enforce the same
permissions, including requests without the workspace header; users with multiple
available numbers must select one.

**Delete user** permanently removes an eligible account, including pending invitations.
Existing access tokens stop working. Campaigns and metrics retain their history with
an empty creator. You cannot delete yourself or a superuser through this screen, and
only owners can delete other owners.

Apply the new history-preservation migrations before using deletion:

```bash
cd Backend
python manage.py migrate
```

## Invitation SMTP configuration

Sign in to `/admin/` as a Django superuser and open **Users → SMTP configuration**.
Add the SMTP host, port, transport security (STARTTLS, SSL/TLS, or no TLS for a relay),
sender email/name, connection timeout, and authentication credentials. Enable and save
it. There is one global SMTP configuration, and changes take effect on the next send
without restarting services. Platform administrators can invite users, but only Django
superusers can manage this server-wide configuration.

The SMTP username and password are stored as Fernet authenticated ciphertext, and admin
shows only that ciphertext. Credential inputs are write-only: leave them blank to retain
the stored values, or enter replacements. No saved plaintext is inserted into the page
or its HTML. Host, port and sender information remain readable because they are not
secrets. Base64 encoding by itself does not protect credentials.

Set `SMTP_ENCRYPTION_KEY` in `Backend/.env` before saving credentials. Generate it once:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Keep this key outside the database and Docker images, and back it up securely alongside
your deployment secrets. The application must decrypt credentials to authenticate to
SMTP; someone with server/key access can therefore decrypt them. Losing or replacing
the key requires restoring it or entering new SMTP credentials. The local deployment
uses the existing Docker `env_file` setting to supply it to backend and worker containers.

Apply migrations and rebuild the backend/worker when installing this feature. SMTP
`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` and `EMAIL_USE_TLS`
environment settings are no longer used; enter those settings in admin instead. If SMTP
is missing, disabled or fails, invitations return a safe error and the database invitation
change is rolled back. A successful response means the SMTP server accepted the email;
it does not guarantee inbox delivery. Set `FRONTEND_URL` to the public frontend address
so invitation links open the correct application.

Implementation references: [Fernet encryption](https://cryptography.io/en/latest/fernet/)
and [Django email backends](https://docs.djangoproject.com/en/5.2/topics/email/).
