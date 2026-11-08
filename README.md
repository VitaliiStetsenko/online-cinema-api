# Online Cinema API

Online Cinema is a FastAPI backend for user accounts, movie catalog management, favorites, ratings, comments, notifications, avatars, and shopping carts.

## Features

- Email registration, activation, password reset, password change, login, logout, JWT refresh, and refresh-token rotation.
- Role-based access for `user`, `moderator`, and `admin`.
- User profiles and validated JPEG, PNG, and WEBP avatar uploads to MinIO.
- Public movie catalog with pagination, search, filters, sorting, and genre movie counts.
- Moderator/admin CRUD for movies, genres, directors, stars, and certifications.
- Favorites, ratings, comments with replies, movie/comment reactions, and in-app notifications.
- Per-user carts with duplicate protection and total-price calculation.
- Celery workers for emails and periodic cleanup of expired tokens.
- Swagger/OpenAPI documentation, Docker Compose, Alembic migrations, strict MyPy, and GitHub Actions CI.

## Technology Stack

- Python 3.11+, FastAPI, Pydantic Settings
- PostgreSQL, SQLAlchemy 2.0 async ORM, Alembic
- Python-JOSE, bcrypt, Redis, Celery, Flower
- MinIO and boto3
- Poetry, Docker, Docker Compose
- Pytest, pytest-asyncio, pytest-cov, Black, Flake8, MyPy

## API Documentation

Swagger and OpenAPI are public. Protected operations still require an access token, which can be supplied with Swagger's **Authorize** button.

| Run mode | Swagger UI | OpenAPI schema |
| --- | --- | --- |
| Docker Compose | `http://localhost:8001/docs` | `http://localhost:8001/openapi.json` |
| Local Uvicorn | `http://localhost:8000/docs` | `http://localhost:8000/openapi.json` |

## Quick Start With Docker

### Requirements

- Docker Desktop with Docker Compose
- Git

```powershell
git clone https://github.com/VitaliiStetsenko/online-cinema-api.git
cd online-cinema-api
Copy-Item .env.example .env
```

Set secure values in `.env`, especially `SECRET_KEY`, SMTP credentials, PostgreSQL credentials, and MinIO credentials.

```env
DATABASE_URL=postgresql+asyncpg://user:password@db:5432/online_cinema
DATABASE_SYNC_URL=postgresql+psycopg://user:password@db:5432/online_cinema
SECRET_KEY=replace-with-a-long-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

FRONTEND_URL=http://localhost:3000
CORS_ORIGINS=http://localhost:3000
AUTH_RATE_LIMIT=5/minute

POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=online_cinema
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
```

Start the stack and apply migrations:

```powershell
docker compose up --build -d
docker compose exec app alembic upgrade head
```

| Service | Address |
| --- | --- |
| API and Swagger | `http://localhost:8001/docs` |
| MinIO API | `http://localhost:9010` |
| MinIO Console | `http://localhost:9011` |

PostgreSQL, Redis, and Flower are intentionally not exposed to the host by default. Use a Docker Compose override only when local debugging requires published ports.

Stop services:

```powershell
docker compose down
```

Remove service data too:

```powershell
docker compose down -v
```

## Local Development

Install dependencies and start the infrastructure services:

```powershell
poetry install
docker compose up -d db redis minio
Copy-Item .env.example .env
```

For a locally running API, configure the host-facing service ports in `.env`:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/online_cinema
DATABASE_SYNC_URL=postgresql+psycopg://user:password@localhost:5432/online_cinema
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
MINIO_ENDPOINT=localhost:9010
```

If you need PostgreSQL or Redis from the host, publish their ports through a local Compose override. Then run:

```powershell
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
```

Start Celery services when testing emails or scheduled cleanup:

```powershell
poetry run celery -A app.tasks.celery_app worker --loglevel=info
poetry run celery -A app.tasks.celery_app beat --loglevel=info
poetry run celery -A app.tasks.celery_app flower --port=5555
```

## Authentication

Protected endpoints require:

```http
Authorization: Bearer <ACCESS_TOKEN>
```

`POST /api/auth/login` returns access and refresh tokens. Refresh tokens are accepted only by `POST /api/auth/refresh`; each successful refresh rotates the stored token.

Passwords must be 8 to 100 characters long and include lowercase, uppercase, numeric, and special characters.

Authentication endpoints are rate-limited according to `AUTH_RATE_LIMIT`.

## API Overview

All routes below are prefixed with `/api` unless otherwise noted. Swagger provides complete request and response schemas.

### Authentication: `/auth`

| Method | Route | Description |
| --- | --- | --- |
| POST | `/register` | Register a user and queue an activation email. |
| POST | `/activate/{token}` | Activate an account using an activation token. |
| POST | `/resend-activation` | Send a new activation token for an inactive account. |
| POST | `/login` | Return an access/refresh JWT pair. |
| POST | `/refresh` | Rotate a refresh token and return a new token pair. |
| POST | `/logout` | Revoke a refresh token. |
| POST | `/change-password` | Change the active user's password. |
| POST | `/request-password-reset` | Queue a password reset email for an active account. |
| POST | `/reset-password` | Set a new password using a reset token. |

Email links target configurable frontend pages: `FRONTEND_URL/activate?token=...` and `FRONTEND_URL/reset-password?token=...`. The frontend must call the matching API endpoint to finish activation or password reset.

### Users: `/users`

| Method | Route | Access | Description |
| --- | --- | --- | --- |
| GET | `/me` | Active user | Get account and profile data. |
| POST | `/me/profile` | Active user | Create a profile. |
| PUT | `/me/profile` | Active user | Update or create a profile. |
| POST | `/me/avatar` | Active user | Upload an `avatar` multipart field, up to 5 MB. |
| GET | `` | Admin | List accounts. |
| PATCH | `/{user_id}` | Admin | Change a role or activation state. |

### Movies: `/movies`

| Method | Route | Access | Description |
| --- | --- | --- | --- |
| GET | `` | Public | Browse movies. |
| GET | `/{movie_id}` | Public | Get movie details. |
| POST | `` | Moderator/admin | Create a movie. |
| PUT | `/{movie_id}` | Moderator/admin | Update a movie. |
| DELETE | `/{movie_id}` | Moderator/admin | Delete a movie not present in a cart. |

Catalog query parameters: `page`, `page_size`, `query`, `genre_id`, `year_from`, `year_to`, `imdb_from`, `imdb_to`, `sort_by`, and `sort_order`. Valid `sort_by` values are `name`, `year`, `imdb`, `price`, and `votes`.

### Catalog Management: `/catalog`

Public `GET` routes are available for `/genres`, `/directors`, `/stars`, `/certifications`, and `/genres/with-counts`.

Moderators and admins can use `POST`, `PUT /{entity_id}`, and `DELETE /{entity_id}` for genres, directors, stars, and certifications. Deleting an entity still used by movies returns `409 Conflict`.

### Favorites: `/favorites`

| Method | Route | Description |
| --- | --- | --- |
| GET | `` | List current user's favorites with catalog filters. |
| POST | `/{movie_id}` | Add a movie to favorites. |
| DELETE | `/{movie_id}` | Remove a movie from favorites. |

### Ratings, Comments, and Notifications

| Method | Route | Description |
| --- | --- | --- |
| PUT | `/movies/{movie_id}/rating` | Set a score from 1 to 10. |
| GET | `/movies/{movie_id}/rating` | Get the average rating and current user's score. |
| POST/GET | `/movies/{movie_id}/comments` | Create or list comments. |
| PUT/DELETE | `/comments/{comment_id}` | Update or delete an owned comment. |
| PUT | `/comments/{comment_id}/reaction?is_like=true` | Set a comment reaction. |
| PUT | `/movies/{movie_id}/reaction?is_like=true` | Set a movie reaction. |
| GET | `/notifications` | List in-app notifications. |
| PATCH | `/notifications/{notification_id}/read` | Mark a notification as read. |

### Cart: `/cart`

| Method | Route | Description |
| --- | --- | --- |
| GET | `` | Get or create the current user's cart. |
| POST | `/{movie_id}` | Add a movie. |
| DELETE | `/{movie_id}` | Remove a movie. |
| DELETE | `` | Clear the cart. |

## Testing and Quality

```powershell
poetry run pytest tests/
poetry run pytest tests/ --cov=app --cov-report=term-missing
poetry run black --check app tests alembic
poetry run flake8 app tests alembic --max-line-length=120 --exclude=__pycache__
poetry run mypy app --ignore-missing-imports
```

Latest local result: **24 passed**, **88% coverage**.

## CI

GitHub Actions runs quality checks for pushes and pull requests to `develop`, `main`, and `fix`. It runs Black, Flake8, strict MyPy, and the SQLite test suite with coverage. A separate job starts PostgreSQL 15 and verifies the full Alembic migration chain.

## Security Notes

- Replace all sample credentials before deployment.
- Configure `CORS_ORIGINS` with only trusted frontend origins.
- Keep Swagger public only for development or trusted deployments.
- The Docker image installs runtime dependencies only; development dependencies are used locally and in CI.

## Author

Vitalii Stetsenko
