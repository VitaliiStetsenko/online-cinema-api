# Online Cinema API
 
Backend API for an online cinema built with FastAPI. The project implements user accounts and roles, a movie catalog, profiles with avatars, favorites, ratings, comments, reactions, notifications, and a shopping cart.
 
## Table of Contents
 
- [Features](#features)
- [Technologies](#technologies)
- [API Documentation](#api-documentation)
- [Quick Start with Docker](#quick-start-with-docker)
- [Local Setup](#local-setup)
- [Authorization](#authorization)
- [API](#api)
- [Tests and Quality](#tests-and-quality)
- [CI](#ci)
## Features
 
### Accounts and Access
 
- Registration with a unique email and password strength validation.
- Account activation with a one-time token valid for 24 hours.
- Re-sending the activation token for an inactive user.
- Login with email and password, issuing a JWT pair: access and refresh.
- The access token is short-lived; the refresh token is stored in the database and is used only to renew the access token.
- Refresh tokens are rotated on every successful refresh and are rejected for inactive accounts.
- Logout revokes the refresh token, so it cannot be used again.
- Password change with verification of the old password, and password reset via a one-time token.
- Three roles: `user`, `moderator`, `admin`.
- An administrator can view users, change their role, and manually activate an account.
### Profile and Avatar
 
- Create, view, and update your own profile.
- Profile fields: first name, last name, gender, date of birth, bio, and avatar URL.
- Upload JPEG, PNG, and WEBP avatars up to 5 MB to MinIO.
- Uploaded image bytes are validated and MinIO object keys do not use the client filename.
### Movie Catalog
 
- Public movie list and detailed movie information.
- Search by title, description, actors, and directors.
- Filters by genre, release year range, and IMDb rating.
- Sorting by title, year, IMDb, price, or number of votes.
- List pagination.
- CRUD for movies, genres, directors, actors, and age certifications for moderator/admin.
- Protection against deleting a movie that is in someone's cart.
- Genre list with the number of related movies.
### Movie Interaction
 
- Favorites with search, filtering, sorting, and pagination.
- Movie ratings from 1 to 10, with the ability to change your own rating.
- Average rating, number of ratings, and the current user's rating.
- Comments, editing and deleting your own comments, and replies to comments.
- Likes and dislikes for comments and movies.
- Internal notifications about replies and reactions to comments.
### Cart and Background Tasks
 
- One cart per user; adding the same movie twice is not allowed.
- View the cart contents and total price, remove an item, and clear the cart completely.
- Celery tasks for activation and password reset emails.
- Celery Beat cleans up expired activation, password-reset, and refresh tokens.
- Redis is used as the Celery broker; Flower provides task monitoring.
- Auth endpoints are rate-limited and browser access is controlled through configurable CORS origins.
## Technologies
 
- Python 3.11+, FastAPI, and Pydantic Settings.
- PostgreSQL, SQLAlchemy Async, and Alembic.
- JWT via Python-JOSE, password hashing via bcrypt.
- Redis, Celery, Celery Beat, and Flower.
- MinIO for S3-compatible avatar storage.
- Docker, Docker Compose, and Poetry.
- Pytest, pytest-asyncio, pytest-cov, Black, Flake8, strict MyPy, and GitHub Actions.
## API Documentation
 
Swagger UI and the OpenAPI schema are available without authorization. Protected methods in Swagger require an access token via the **Authorize** button.
 
| Run mode | Swagger UI | OpenAPI JSON |
| --- | --- | --- |
| Docker Compose | `http://localhost:8001/docs` | `http://localhost:8001/openapi.json` |
| Local Uvicorn | `http://localhost:8000/docs` | `http://localhost:8000/openapi.json` |
 
Swagger contains request and response schemas, required parameters, and response codes for all endpoints. The sections below serve as a brief API map and a description of custom actions.
 
## Quick Start with Docker
 
### Requirements
 
- Docker Desktop with Docker Compose.
- Git.
### 1. Clone and Configure
 
```powershell
git clone https://github.com/VitaliiStetsenko/Online-Cinema-Portfolio-Project-.git
cd Online-Cinema-Portfolio-Project-
git checkout develop
Copy-Item .env.example .env
```
 
Be sure to replace `SECRET_KEY` in `.env`. To send real emails, provide working SMTP credentials.
 
Main settings:
 
```env
DATABASE_URL=postgresql+asyncpg://user:password@db:5432/online_cinema
DATABASE_SYNC_URL=postgresql+psycopg://user:password@db:5432/online_cinema
SECRET_KEY=replace-with-a-long-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
FRONTEND_URL=http://localhost:3000
CORS_ORIGINS=http://localhost:3000
AUTH_RATE_LIMIT=5/minute
 
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
 
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
 
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=avatars
MINIO_SECURE=false
```
 
### 2. Start and Migrate
 
```powershell
docker compose up --build -d
docker compose exec app alembic upgrade head
```
 
### Services
 
| Service | Address |
| --- | --- |
| API and Swagger | `http://localhost:8001/docs` |
| MinIO API | `http://localhost:9010` |
| MinIO Console | `http://localhost:9011` |
 
Stop the services:
 
```powershell
docker compose down
```
 
Also remove the PostgreSQL and MinIO volumes:
 
```powershell
docker compose down -v
```
 
## Local Setup
 
This mode runs FastAPI on your machine while keeping PostgreSQL, Redis, and MinIO in Docker.
 
```powershell
poetry install
docker compose up -d db redis minio
Copy-Item .env.example .env
```
 
For the local `.env`, replace the Docker service names:
 
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/online_cinema
DATABASE_SYNC_URL=postgresql+psycopg://user:password@localhost:5432/online_cinema
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
MINIO_ENDPOINT=localhost:9010
```
 
Apply the migrations and start the API:
 
```powershell
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
```
 
Local Swagger: `http://localhost:8000/docs`.
 
If needed, start Celery separately:
 
```powershell
poetry run celery -A app.tasks.celery_app worker --loglevel=info
poetry run celery -A app.tasks.celery_app beat --loglevel=info
poetry run celery -A app.tasks.celery_app flower --port=5555
```
 
## Authorization
 
Most user actions require the header:
 
```http
Authorization: Bearer <ACCESS_TOKEN>
```
 
Get tokens via `POST /api/auth/login`. In Swagger, click **Authorize**, paste only the access token value, and confirm. The refresh token is intended exclusively for `POST /api/auth/refresh` and does not grant access to protected endpoints.
 
The password must be 8 to 100 characters long and contain a lowercase letter, an uppercase letter, a digit, and a special character.
 
## API
 
All listed paths start with `/api` unless stated otherwise. Full JSON schemas are available in Swagger.
 
### Service Routes
 
| Method | Path | Access | Action |
| --- | --- | --- | --- |
| GET | `/` | public | Health check: returns the API status. |
| GET | `/docs` | public | Swagger UI. |
| GET | `/openapi.json` | public | OpenAPI schema. |
 
### Authentication: `/auth`
 
| Method | Path | Parameters/Body | Action |
| --- | --- | --- | --- |
| POST | `/register` | `email`, `password` | Creates an inactive user and queues sending of the activation token. |
| POST | `/activate/{token}` | path `token` | Activates the account using a valid token. |
| POST | `/resend-activation` | `email` | Issues a new activation token for an inactive user. |
| POST | `/login` | `email`, `password` | Returns `access_token`, `refresh_token`, `token_type`. |
| POST | `/refresh` | `refresh_token` | Creates a new access token. |
| POST | `/logout` | `refresh_token` | Deletes the refresh token from the database. |
| POST | `/change-password` | `old_password`, `new_password` | Changes the current user's password. Requires an access token. |
| POST | `/request-password-reset` | `email` | Creates and sends a reset token for an active user. |
| POST | `/reset-password` | `token`, `new_password` | Sets a new password using a valid reset token. |
 
Registration example for Docker:
 
```powershell
curl.exe -X POST "http://localhost:8001/api/auth/register" `
  -H "Content-Type: application/json" `
  -d "{\"email\": \"user@example.com\", \"password\": \"SecurePass123!\"}"
```
 
### Users: `/users`
 
| Method | Path | Access | Action |
| --- | --- | --- | --- |
| GET | `/me` | active user | Returns the current user's account and profile. |
| POST | `/me/profile` | active user | Creates a profile. Body: `first_name`, `last_name`, `gender`, `date_of_birth`, `info`. |
| PUT | `/me/profile` | active user | Updates the profile; creates it automatically if it does not exist. |
| POST | `/me/avatar` | active user | Uploads the multipart field `avatar` as JPEG, PNG, or WEBP up to 5 MB. |
| GET | `` | admin | Returns a list of user accounts. |
| PATCH | `/{user_id}` | admin | Changes `group` (`user`, `moderator`, `admin`) and/or `is_active`. |
 
### Movies: `/movies`
 
| Method | Path | Access | Action |
| --- | --- | --- | --- |
| GET | `` | public | Returns the paginated catalog. |
| GET | `/{movie_id}` | public | Returns the detailed movie card. |
| POST | `` | moderator/admin | Creates a movie. |
| PUT | `/{movie_id}` | moderator/admin | Updates the movie fields and its relations. |
| DELETE | `/{movie_id}` | moderator/admin | Deletes the movie if it is not in any cart. |
 
`GET /movies` parameters:
 
| Parameter | Value | Purpose |
| --- | --- | --- |
| `page`, `page_size` | `1`, `1..100` | Page and number of results. |
| `query` | string | Search by title, description, actor, and director. |
| `genre_id` | integer | Genre filter. |
| `year_from`, `year_to` | `1888..2100` | Release year range. |
| `imdb_from`, `imdb_to` | `0..10` | IMDb range. |
| `sort_by` | `name`, `year`, `imdb`, `price`, `votes` | Sort field. |
| `sort_order` | `asc`, `desc` | Sort direction. |
 
The movie creation body contains `name`, `year`, `time`, `imdb`, `votes`, `description`, `price`, `certification_id`, and the optional arrays `genre_ids`, `director_ids`, `star_ids`. `meta_score` and `gross` are also available.
 
### Catalog Reference Data: `/catalog`
 
| Resource | Public | Moderator/admin |
| --- | --- | --- |
| `/genres` | `GET` | `POST`, `PUT /{entity_id}`, `DELETE /{entity_id}` |
| `/directors` | `GET` | `POST`, `PUT /{entity_id}`, `DELETE /{entity_id}` |
| `/stars` | `GET` | `POST`, `PUT /{entity_id}`, `DELETE /{entity_id}` |
| `/certifications` | `GET` | `POST`, `PUT /{entity_id}`, `DELETE /{entity_id}` |
| `/genres/with-counts` | `GET` | - |
 
Creation uses the body `{ "name": "..." }`. Update accepts the same body. The `GET /genres/with-counts` endpoint returns `id`, `name`, and `movie_count` for each genre.
 
### Favorites: `/favorites`
 
| Method | Path | Action |
| --- | --- | --- |
| GET | `` | Returns the current user's paginated list of favorite movies. |
| POST | `/{movie_id}` | Adds a movie to favorites. Adding it again is rejected. |
| DELETE | `/{movie_id}` | Removes a movie from favorites. |
 
`GET /favorites` supports the catalog parameters: `page`, `page_size`, `query`, `genre_id`, `year_from`, `year_to`, `imdb_from`, `imdb_to`, `sort_by`, `sort_order`. `added_at` is also available for `sort_by`.
 
### Ratings, Comments, and Notifications
 
| Method | Path | Action |
| --- | --- | --- |
| PUT | `/movies/{movie_id}/rating` | Creates or updates your own rating. Body: `{ "score": 1..10 }`. |
| GET | `/movies/{movie_id}/rating` | Returns the average score, number of ratings, and the current user's rating. |
| POST | `/movies/{movie_id}/comments` | Creates a comment. Body: `text`, optional `parent_comment_id`. |
| GET | `/movies/{movie_id}/comments` | Returns the movie's comments with reaction counts. |
| PUT | `/comments/{comment_id}` | Edits your own comment. Body: `text`. |
| DELETE | `/comments/{comment_id}` | Deletes your own comment. |
| PUT | `/comments/{comment_id}/reaction?is_like=true` | Sets or changes a like/dislike on a comment. |
| PUT | `/movies/{movie_id}/reaction?is_like=true` | Sets or changes a like/dislike on a movie. |
| GET | `/notifications` | Returns the current user's notifications. |
| PATCH | `/notifications/{notification_id}/read` | Marks a notification as read. |
 
All methods in this section require an active user.
 
### Cart: `/cart`
 
| Method | Path | Action |
| --- | --- | --- |
| GET | `` | Returns the current cart, its items, and `total_price`; creates an empty cart on the first call. |
| POST | `/{movie_id}` | Adds a movie to the cart. Adding it again is rejected. |
| DELETE | `/{movie_id}` | Removes the specified item. |
| DELETE | `` | Clears the cart. |
 
All cart methods require an active user.
 
## Tests and Quality
 
The tests use a separate in-memory SQLite database. Docker, PostgreSQL, Redis, SMTP, and MinIO are not needed to run them: external calls are isolated in the tests.
 
```powershell
# All tests
poetry run pytest tests/
 
# Code coverage
poetry run pytest tests/ --cov=app --cov-report=term-missing
 
# HTML coverage report
poetry run pytest tests/ --cov=app --cov-report=html
 
# Formatting, linter, and types
poetry run black --check app tests
poetry run flake8 app tests --max-line-length=120 --exclude=__pycache__
poetry run mypy app --ignore-missing-imports
```
 
Latest local check: **22 passed**, overall line coverage **87%**.
 
## CI
 
GitHub Actions runs on `push` and pull requests to the `develop` and `main` branches. The pipeline installs dependencies via Poetry, runs Black, Flake8, MyPy, and Pytest with coverage, and uploads `coverage.xml` to Codecov. Configuration: `.github/workflows/ci.yml`.
 
## Important Notes
 
- Before real-world use, change the `SECRET_KEY`, SMTP password, and MinIO credentials from `.env.example`.
- Docker Compose is configured for development: the source code is mounted into the container, and Uvicorn runs with `--reload`.
- After the first Docker start, apply the migrations with `docker compose exec app alembic upgrade head`.
- Emails are sent by the Celery worker via SMTP. Complete activation and password reset by calling the API from Swagger or a client application, passing the token to `POST /api/auth/activate/{token}` or `POST /api/auth/reset-password`.
- Swagger and OpenAPI are public; access to user, moderator, and administrator actions is restricted by JWT and roles.
## Author
 
Vitalii Stetsenko
 
---------------------------------------------------------------------------------------------------

# Online Cinema API

Backend API для онлайн-кинотеатра на FastAPI. Проект реализует учетные записи и роли, каталог фильмов, профиль с аватаром, избранное, оценки, комментарии, реакции, уведомления и корзину.

## Содержание

- [Возможности](#возможности)
- [Технологии](#технологии)
- [Документация API](#документация-api)
- [Быстрый запуск в Docker](#быстрый-запуск-в-docker)
- [Локальный запуск](#локальный-запуск)
- [Авторизация](#авторизация)
- [API](#api)
- [Тесты и качество](#тесты-и-качество)
- [CI](#ci)

## Возможности

### Учетные записи и доступ

- Регистрация по уникальному email с проверкой сложности пароля.
- Активация учетной записи по одноразовому токену, действующему 24 часа.
- Повторная отправка activation-токена для неактивного пользователя.
- Вход по email и паролю с выдачей пары JWT: access и refresh.
- Access token действует ограниченное время, refresh token хранится в базе и используется только для обновления access token.
- Logout отзывает refresh token, поэтому его нельзя использовать повторно.
- Смена пароля с проверкой старого пароля и сброс пароля по одноразовому токену.
- Три роли: `user`, `moderator`, `admin`.
- Администратор может просматривать пользователей, менять роль и вручную активировать аккаунт.

### Профиль и аватар

- Создание, просмотр и изменение своего профиля.
- Поля профиля: имя, фамилия, пол, дата рождения, информация о себе и адрес аватара.
- Загрузка JPEG, PNG и WEBP-аватаров размером до 5 MB в MinIO.

### Каталог фильмов

- Публичный список и подробная информация о фильмах.
- Поиск по названию, описанию, актерам и режиссерам.
- Фильтры по жанру, диапазону годов выпуска и IMDb-рейтингу.
- Сортировка по названию, году, IMDb, цене или числу голосов.
- Пагинация списка.
- CRUD фильмов, жанров, режиссеров, актеров и возрастных сертификатов для moderator/admin.
- Защита от удаления фильма, который находится в чьей-либо корзине.
- Список жанров с количеством связанных фильмов.

### Взаимодействие с фильмами

- Избранное с поиском, фильтрацией, сортировкой и пагинацией.
- Оценки фильмов от 1 до 10 с возможностью изменить свою оценку.
- Средняя оценка, количество оценок и оценка текущего пользователя.
- Комментарии, редактирование и удаление собственных комментариев, ответы на комментарии.
- Лайки и дизлайки комментариев и фильмов.
- Внутренние уведомления об ответах и реакциях на комментарии.

### Корзина и фоновые задачи

- Одна корзина на пользователя, запрет повторного добавления фильма.
- Просмотр состава корзины и общей стоимости, удаление позиции и полная очистка.
- Celery-задачи для писем об активации и сбросе пароля.
- Celery Beat очищает истекшие activation, password-reset и refresh токены.
- Redis используется как брокер Celery, Flower предоставляет мониторинг задач.

## Технологии

- Python 3.11+, FastAPI и Pydantic Settings.
- PostgreSQL, SQLAlchemy Async и Alembic.
- JWT через Python-JOSE, хеширование паролей через bcrypt.
- Redis, Celery, Celery Beat и Flower.
- MinIO для S3-совместимого хранения аватаров.
- Docker, Docker Compose и Poetry.
- Pytest, pytest-asyncio, pytest-cov, Black, Flake8, MyPy и GitHub Actions.

## Документация API

Swagger UI и OpenAPI-схема открыты без авторизации. Защищенные методы в Swagger требуют access token через кнопку **Authorize**.

| Режим запуска | Swagger UI | OpenAPI JSON |
| --- | --- | --- |
| Docker Compose | `http://localhost:8001/docs` | `http://localhost:8001/openapi.json` |
| Локальный Uvicorn | `http://localhost:8000/docs` | `http://localhost:8000/openapi.json` |

Swagger содержит схемы запросов, ответов, обязательные параметры и коды ответов для всех endpoint. Разделы ниже служат краткой картой API и описанием кастомных действий.

## Быстрый запуск в Docker

### Требования

- Docker Desktop с Docker Compose.
- Git.

### 1. Клонирование и конфигурация

```powershell
git clone https://github.com/VitaliiStetsenko/Online-Cinema-Portfolio-Project-.git
cd Online-Cinema-Portfolio-Project-
git checkout develop
Copy-Item .env.example .env
```

В `.env` обязательно замените `SECRET_KEY`. Для отправки реальных email укажите рабочие SMTP-данные.

Основные настройки:

```env
DATABASE_URL=postgresql+asyncpg://user:password@db:5432/online_cinema
SECRET_KEY=replace-with-a-long-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com

REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=avatars
MINIO_SECURE=false
```

### 2. Запуск и миграции

```powershell
docker compose up --build -d
docker compose exec app alembic upgrade head
```

### Сервисы

| Сервис | Адрес |
| --- | --- |
| API и Swagger | `http://localhost:8001/docs` |
| Flower | `http://localhost:5555` |
| MinIO API | `http://localhost:9010` |
| MinIO Console | `http://localhost:9011` |
| PostgreSQL | `localhost:5432` |
| Redis | `localhost:6379` |

Остановить сервисы:

```powershell
docker compose down
```

Удалить также тома PostgreSQL и MinIO:

```powershell
docker compose down -v
```

## Локальный запуск

Этот режим запускает FastAPI на компьютере, а PostgreSQL, Redis и MinIO оставляет в Docker.

```powershell
poetry install
docker compose up -d db redis minio
Copy-Item .env.example .env
```

Для локального `.env` замените имена Docker-сервисов:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/online_cinema
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
MINIO_ENDPOINT=localhost:9010
```

Примените миграции и запустите API:

```powershell
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
```

Локальный Swagger: `http://localhost:8000/docs`.

При необходимости отдельно запустите Celery:

```powershell
poetry run celery -A app.tasks.celery_app worker --loglevel=info
poetry run celery -A app.tasks.celery_app beat --loglevel=info
poetry run celery -A app.tasks.celery_app flower --port=5555
```

## Авторизация

Большинство действий пользователя требуют заголовок:

```http
Authorization: Bearer <ACCESS_TOKEN>
```

Получите токены через `POST /api/auth/login`. В Swagger нажмите **Authorize**, вставьте только значение access token и подтвердите. Refresh token предназначен исключительно для `POST /api/auth/refresh` и не дает доступа к защищенным endpoint.

Пароль должен быть длиной от 8 до 100 символов и содержать строчную и заглавную буквы, цифру и специальный символ.

## API

Все перечисленные пути начинаются с `/api`, если не указано иное. Полные схемы JSON находятся в Swagger.

### Служебные маршруты

| Метод | Путь | Доступ | Действие |
| --- | --- | --- | --- |
| GET | `/` | public | Health check: возвращает статус API. |
| GET | `/docs` | public | Swagger UI. |
| GET | `/openapi.json` | public | OpenAPI-схема. |

### Аутентификация: `/auth`

| Метод | Путь | Параметры/тело | Действие |
| --- | --- | --- | --- |
| POST | `/register` | `email`, `password` | Создает неактивного пользователя и ставит отправку activation-токена в очередь. |
| POST | `/activate/{token}` | path `token` | Активирует аккаунт по действующему токену. |
| POST | `/resend-activation` | `email` | Выпускает новый activation-токен для неактивного пользователя. |
| POST | `/login` | `email`, `password` | Возвращает `access_token`, `refresh_token`, `token_type`. |
| POST | `/refresh` | `refresh_token` | Создает новый access token. |
| POST | `/logout` | `refresh_token` | Удаляет refresh token из базы. |
| POST | `/change-password` | `old_password`, `new_password` | Меняет пароль текущего пользователя. Требует access token. |
| POST | `/request-password-reset` | `email` | Создает и отправляет reset-токен для активного пользователя. |
| POST | `/reset-password` | `token`, `new_password` | Устанавливает новый пароль по действующему reset-токену. |

Пример регистрации для Docker:

```powershell
curl.exe -X POST "http://localhost:8001/api/auth/register" `
  -H "Content-Type: application/json" `
  -d "{\"email\": \"user@example.com\", \"password\": \"SecurePass123!\"}"
```

### Пользователи: `/users`

| Метод | Путь | Доступ | Действие |
| --- | --- | --- | --- |
| GET | `/me` | active user | Возвращает аккаунт и профиль текущего пользователя. |
| POST | `/me/profile` | active user | Создает профиль. Тело: `first_name`, `last_name`, `gender`, `date_of_birth`, `info`. |
| PUT | `/me/profile` | active user | Обновляет профиль; создает его автоматически, если профиля нет. |
| POST | `/me/avatar` | active user | Загружает multipart-поле `avatar` в JPEG, PNG или WEBP до 5 MB. |
| GET | `` | admin | Возвращает список учетных записей. |
| PATCH | `/{user_id}` | admin | Меняет `group` (`user`, `moderator`, `admin`) и/или `is_active`. |

### Фильмы: `/movies`

| Метод | Путь | Доступ | Действие |
| --- | --- | --- | --- |
| GET | `` | public | Возвращает постраничный каталог. |
| GET | `/{movie_id}` | public | Возвращает подробную карточку фильма. |
| POST | `` | moderator/admin | Создает фильм. |
| PUT | `/{movie_id}` | moderator/admin | Обновляет поля фильма и его связи. |
| DELETE | `/{movie_id}` | moderator/admin | Удаляет фильм, если его нет в корзинах. |

Параметры `GET /movies`:

| Параметр | Значение | Назначение |
| --- | --- | --- |
| `page`, `page_size` | `1`, `1..100` | Страница и число результатов. |
| `query` | строка | Поиск по названию, описанию, актеру и режиссеру. |
| `genre_id` | integer | Фильтр по жанру. |
| `year_from`, `year_to` | `1888..2100` | Диапазон года выпуска. |
| `imdb_from`, `imdb_to` | `0..10` | Диапазон IMDb. |
| `sort_by` | `name`, `year`, `imdb`, `price`, `votes` | Поле сортировки. |
| `sort_order` | `asc`, `desc` | Направление сортировки. |

Тело создания фильма содержит `name`, `year`, `time`, `imdb`, `votes`, `description`, `price`, `certification_id` и необязательные массивы `genre_ids`, `director_ids`, `star_ids`. Дополнительно доступны `meta_score` и `gross`.

### Управление справочниками: `/catalog`

| Ресурс | Public | Moderator/admin |
| --- | --- | --- |
| `/genres` | `GET` | `POST`, `PUT /{entity_id}`, `DELETE /{entity_id}` |
| `/directors` | `GET` | `POST`, `PUT /{entity_id}`, `DELETE /{entity_id}` |
| `/stars` | `GET` | `POST`, `PUT /{entity_id}`, `DELETE /{entity_id}` |
| `/certifications` | `GET` | `POST`, `PUT /{entity_id}`, `DELETE /{entity_id}` |
| `/genres/with-counts` | `GET` | - |

Создание использует тело `{ "name": "..." }`. Обновление принимает такое же тело. Endpoint `GET /genres/with-counts` возвращает для каждого жанра `id`, `name` и `movie_count`.

### Избранное: `/favorites`

| Метод | Путь | Действие |
| --- | --- | --- |
| GET | `` | Возвращает постраничный список избранных фильмов текущего пользователя. |
| POST | `/{movie_id}` | Добавляет фильм в избранное. Повторное добавление отклоняется. |
| DELETE | `/{movie_id}` | Удаляет фильм из избранного. |

`GET /favorites` поддерживает параметры каталога: `page`, `page_size`, `query`, `genre_id`, `year_from`, `year_to`, `imdb_from`, `imdb_to`, `sort_by`, `sort_order`. Для `sort_by` также доступно `added_at`.

### Оценки, комментарии и уведомления

| Метод | Путь | Действие |
| --- | --- | --- |
| PUT | `/movies/{movie_id}/rating` | Создает или изменяет свою оценку. Тело: `{ "score": 1..10 }`. |
| GET | `/movies/{movie_id}/rating` | Возвращает средний балл, количество оценок и оценку текущего пользователя. |
| POST | `/movies/{movie_id}/comments` | Создает комментарий. Тело: `text`, необязательный `parent_comment_id`. |
| GET | `/movies/{movie_id}/comments` | Возвращает комментарии фильма с количеством реакций. |
| PUT | `/comments/{comment_id}` | Изменяет собственный комментарий. Тело: `text`. |
| DELETE | `/comments/{comment_id}` | Удаляет собственный комментарий. |
| PUT | `/comments/{comment_id}/reaction?is_like=true` | Ставит или изменяет лайк/дизлайк комментария. |
| PUT | `/movies/{movie_id}/reaction?is_like=true` | Ставит или изменяет лайк/дизлайк фильма. |
| GET | `/notifications` | Возвращает уведомления текущего пользователя. |
| PATCH | `/notifications/{notification_id}/read` | Помечает уведомление прочитанным. |

Все методы этого раздела требуют активного пользователя.

### Корзина: `/cart`

| Метод | Путь | Действие |
| --- | --- | --- |
| GET | `` | Возвращает текущую корзину, позиции и `total_price`; при первом вызове создает пустую корзину. |
| POST | `/{movie_id}` | Добавляет фильм в корзину. Повторное добавление отклоняется. |
| DELETE | `/{movie_id}` | Удаляет указанную позицию. |
| DELETE | `` | Очищает корзину. |

Все методы корзины требуют активного пользователя.

## Тесты и качество

Тесты используют отдельную SQLite in-memory базу. Для запуска не нужны Docker, PostgreSQL, Redis, SMTP или MinIO: внешние вызовы изолируются в тестах.

```powershell
# Все тесты
poetry run pytest tests/

# Покрытие кода
poetry run pytest tests/ --cov=app --cov-report=term-missing

# HTML-отчет покрытия
poetry run pytest tests/ --cov=app --cov-report=html

# Форматирование, линтер и типы
poetry run black --check app tests
poetry run flake8 app tests --max-line-length=120 --exclude=__pycache__
poetry run mypy app --ignore-missing-imports
```

Последняя локальная проверка: **24 passed**.

## CI

GitHub Actions runs for pushes and pull requests targeting `develop`, `main`, and `fix`. The quality job installs dependencies through Poetry, runs Black, Flake8, strict MyPy, Pytest with coverage, and uploads `coverage.xml` to Codecov. A separate PostgreSQL job starts PostgreSQL 15 and applies the complete Alembic migration chain. Configuration: `.github/workflows/ci.yml`.

## Важные замечания

- Перед реальным использованием смените значения `SECRET_KEY`, SMTP-пароль и MinIO credentials из `.env.example`.
- В Docker-образ устанавливаются только runtime-зависимости; dev-зависимости используются в локальной среде и CI.
- После первого Docker-запуска примените миграции командой `docker compose exec app alembic upgrade head`.
- Письма ведут на настраиваемый frontend (`FRONTEND_URL`): `/activate?token=...` и `/reset-password?token=...`. Frontend должен завершить flow вызовом `POST /api/auth/activate/{token}` или `POST /api/auth/reset-password`.
- PostgreSQL, Redis и Flower не опубликованы наружу в Docker Compose. Для локальной отладки публикуйте нужные порты отдельным override-файлом.
- Swagger и OpenAPI публичны; доступ к пользовательским, модераторским и административным действиям ограничивается JWT и ролями.

## Автор

Vitalii Stetsenko
