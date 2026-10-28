# DineTogether

## Overview

**DineTogether** is a table booking and venue management API built with **FastAPI**. Customers can book tables, while staff manage venues, availability, menus, and reservations.

Access is controlled by three roles:

* **USER** — book tables and manage their own profile.
* **MANAGER** — manage venues and associated resources.
* **ADMIN** — full access to the system, including user management.

## Features

* **Accounts:** registration, authentication with an email address or phone number and a password, JWT access tokens, password changes, profile updates, and user management.
* **Venue management:** create and update venues, assign managers, and manage tables and booking time slots, including their active status.
* **Bookings:** reserve one or more tables, choose time slots, specify the number of guests, and view or update reservations.
* **Menus and images:** manage dishes across venues, control their active status, and upload and retrieve images.
* **Email notifications:** booking confirmations and reminders for customers, and notifications about new and updated bookings for venue managers.
* **Logging:** record user actions, system events, and application errors.

## Tech stack

* **API:** Python 3.12+, FastAPI, Pydantic, Uvicorn, JWT authentication.
* **Database:** PostgreSQL, asynchronous SQLAlchemy, Alembic migrations.
* **Background tasks:** Celery with RabbitMQ; Flower monitoring in the VS Code dev container.
* **Infrastructure:** Docker, Docker Compose, Nginx.
* **Local email testing:** MailDev.

## Setup

### Prerequisites and configuration

Install Docker with Docker Compose v2. The shell examples below use Bash.

Clone the repository:

```bash
git clone https://github.com/humanpride/DineTogether.git
cd DineTogether
```

Create the environment file:

```bash
cd infra
cp .env.example .env
```

Replace the placeholders in `infra/.env` before starting the containers:

| Settings | Configuration |
| --- | --- |
| `TITLE`, `VERSION`, `DESCRIPTION` | Application metadata displayed in the API documentation. |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Database credentials and database name. |
| `POSTGRES_SERVER`, `POSTGRES_PORT` | Use `db` and `5432` for the supplied Compose configurations. |
| `RABBITMQ_DEFAULT_USER`, `RABBITMQ_DEFAULT_PASS` | RabbitMQ credentials. Keep `CELERY_BROKER` pointed at `rabbitmq:5672` with matching credentials. |
| `FROM_EMAIL`, `SMTP_HOST`, `SMTP_PORT` | Sender address and SMTP connection. For local MailDev, use `maildev` and `1025`, with a valid test sender address. For production, use an SMTP server that permits sending from the application without SMTP authentication; the current implementation does not supply an SMTP username or password. |
| `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` | Set a strong JWT signing secret; the template uses `HS256` and a 30-minute token lifetime. |
| `ADMIN_EMAIL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD` | Credentials for the initial administrator. Replace the example values. |
| `DOCKER_USER` | Docker Hub account hosting the `dinetogether:latest` image, required for production. |

On API startup, the application creates an administrator using `ADMIN_*` if no user with `ADMIN_EMAIL` exists. Subsequent starts leave that existing user unchanged.

### Local development with Docker Compose

From `infra`, build the application and start PostgreSQL, RabbitMQ, Nginx, and MailDev:

```bash
docker compose -p dinetogether -f docker-compose-develop.yaml up -d --build
```

The API is available at `http://127.0.0.1:8000`, or through Nginx at `http://127.0.0.1:888`. MailDev's inbox is available at `http://127.0.0.1:1080`.

The application container starts a Celery worker automatically. This Compose configuration publishes port `5555` but does not start Flower; the VS Code debugging workflow below starts it inside the dev container.

### Production

From `infra`, start the services using the published application image:

```bash
docker compose -p dinetogether -f docker-compose.yaml up -d
```

This configuration uses `${DOCKER_USER}/dinetogether:latest` rather than building from local source. Nginx exposes the API on the server's loopback address at `http://127.0.0.1:888`. Public access requires a separately configured reverse proxy or equivalent routing.

Flower is disabled in production. The Celery worker runs inside the application container.

### Debugging in the VS Code dev container

This workflow is an alternative to local development with Docker Compose above. Run one setup at a time: both configurations publish the same host ports. Open the repository root in VS Code and run **Dev Containers: Reopen in Container** from the Command Palette before starting a debugging session.

The dev container runs alongside supporting services and provides the Python environment for interactive debugging. Its post-create hook installs dependencies, and its post-start hook applies database migrations. The API runs inside `dev` under the VS Code debugger; this workflow does not require a separate `app` container.

Select **FastAPI server** in VS Code and press **F5**. The local `.vscode/launch.json` configuration starts Uvicorn through `debugpy` with reload enabled. Its **Start Celery and Flower** pre-launch task starts both processes inside the same dev container, as configured in `.vscode/tasks.json`. Set breakpoints in the API code and send requests to `http://127.0.0.1:8000` to debug request handling.

Flower is available at `http://127.0.0.1:5555/flower/`; its task uses the `/flower` URL prefix. No separate Flower container is needed.

The `.vscode` launch and task files are ignored by Git. On a fresh checkout, configure them locally to use this F5 workflow.

## Database migrations

Migrations are included in `src/migrations`. No separate migration command is needed for a normal container startup:

* **Local and production Compose:** the application entrypoint waits for PostgreSQL to accept connections, runs `alembic upgrade head`, then starts the Celery worker and Uvicorn. This runs each time the application container starts; Alembic applies any pending migrations.
* **VS Code dev container:** `postStartCommand` invokes `.devcontainer/entrypoint.sh`, which waits for PostgreSQL and runs `uv run alembic upgrade head` from `/workspace/src`. This hook runs when VS Code starts the dev container; it is not a Compose entrypoint.

If a migration fails, the application entrypoint preserves the original Alembic/SQLAlchemy diagnostic output, prints an explicit error with the exit code, and exits with that code. Neither the Celery worker nor the API starts. The dev container script also stops on migration failure.

With detached startup (`up -d`), output is written to the container logs rather than streamed to your terminal. From `infra`, follow production startup logs with:

```bash
docker compose -p dinetogether -f docker-compose.yaml logs --follow --tail=100 app
```

A failed migration ends with a message like this, after the original diagnostic output:

```text
[startup] ERROR: Database migration failed (exit code 1).
[startup] See the Alembic/SQLAlchemy output above for the failing migration and database error.
[startup] Aborting startup: the Celery worker and API will not be started.
```

The exit code depends on the underlying error. Fix the reported cause before restarting. A successful `up -d` alone does not confirm migration success. The deployment workflow uses `up -d --wait --wait-timeout 120` and an HTTP health check against `/openapi.json` to wait for the API. If startup fails or times out, it prints the application logs (including migration diagnostics) and container status, then fails the deployment step. For manual deployment, use the same `--wait --wait-timeout 120` options and inspect the logs if the command fails.

For manual maintenance, run commands inside the application container. From `infra`, for local development:

```bash
docker compose -p dinetogether -f docker-compose-develop.yaml exec app alembic upgrade head
```

Roll back the most recent migration:

```bash
docker compose -p dinetogether -f docker-compose-develop.yaml exec app alembic downgrade -1
```

For production, use `-f docker-compose.yaml` instead. Restarting the application container applies pending migrations again, including a migration previously rolled back manually.

## API documentation

FastAPI generates interactive documentation from the API schemas:

| Interface | Through Nginx (local or on the production server) | Direct access (local Compose) |
| --- | --- | --- |
| Swagger UI | [Swagger UI](http://127.0.0.1:888/docs) | [Swagger UI](http://127.0.0.1:8000/docs) |
| ReDoc | [ReDoc](http://127.0.0.1:888/redoc) | [ReDoc](http://127.0.0.1:8000/redoc) |

## Author

**Sergei Pashkovskii**

[![GitHub](https://img.shields.io/badge/GitHub-humanpride-181717?logo=github\&logoColor=white)](https://github.com/humanpride)

[![Telegram](https://img.shields.io/badge/Telegram-@bronze_beard8-2CA5E0?logo=telegram\&logoColor=white)](https://t.me/bronze_beard8)
