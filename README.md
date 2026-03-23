# Phone Validator Service

Full-stack сервис для CRM webhook-валидации телефонов с нормализацией в E.164, fallback-исправлением через OpenAI `gpt-4o-mini` и SPA-дашбордом с метриками.

## Stack
- Backend: FastAPI + SQLAlchemy (async) + PostgreSQL
- Frontend: React + TypeScript + Vite
- Infra: Docker Compose

## Project Structure
- `app` - backend API, доменная логика, сервисы, репозитории.
- `tests` - unit/integration тесты backend.
- `pyproject.toml` - backend зависимости и инструменты качества.
- `Dockerfile.backend` - сборка backend контейнера.
- `frontend` - SPA дашборд метрик.
- `docker-compose.yml` - запуск полного стека.

## Quick Start
1. Скопируйте env:
   - `copy .env.example .env` (Windows PowerShell)
2. Укажите `OPENAI_API_KEY` в `.env`.
3. Запустите:
   - `docker-compose up --build`
4. URLs:
   - App (через Nginx): `http://localhost:8005`
   - API health (через Nginx): `http://localhost:8005/health`

Nginx поднимается автоматически как контейнер `nginx` и проксирует:
- `/` -> `frontend:5173`
- `/api/*` -> `backend:8000/api/*`

PostgreSQL наружу не публикуется. Доступ к БД только внутри Docker-сети.

## API
### `POST /api/v1/webhooks/crm/lead`
Принимает CRM payload (минимально: `ID`, `CONTACT_PHONE`) и возвращает:
- `status`: `valid | invalid`
- `normalized_phone`: E.164 при успехе
- `reason`: причина отказа при неуспехе
- `source`: `deterministic | llm`

Пример запроса:
```json
{
  "ID": "190326",
  "TITLE": "New deal from Laura Palmer",
  "CONTACT_PHONE": "8-800-555-3535"
}
```

### `GET /api/v1/metrics/summary`
Возвращает total/valid/invalid/success_rate и breakdown причин отказа.

### `GET /api/v1/metrics/timeseries?days=7`
Возвращает динамику по дням за период.

### `GET /api/v1/metrics/recent?limit=20`
Возвращает последние обработанные лиды для таблицы на дашборде.

## Validation Strategy
1. Deterministic stage:
   - пустые/короткие/слишком длинные значения
   - нечисловые и повторяющиеся значения
   - базовая проверка country code
   - нормализация к E.164
2. LLM stage (`gpt-4o-mini`):
   - только для recoverable кейсов
   - structured JSON output
   - retry до 3 попыток
   - обязательная post-validation детерминированным валидатором

## Webhook Security
- Можно включить проверку заголовка `X-Webhook-Token` через `.env`:
  - `WEBHOOK_TOKEN=your_secret`
- Если токен не задан, проверка отключена.

## Local Development
Backend:
- `pip install -e .[dev]`
- `alembic upgrade head`
- `uvicorn app.main:app --reload`

Frontend:
- `cd frontend`
- `npm install`
- `npm run dev`

## Tests
- `pytest`

## Database Migrations (Alembic)
- Миграции находятся в `migrations/versions`.
- В Docker backend контейнер автоматически выполняет `alembic upgrade head` перед запуском API.
- Если БД еще не готова, backend делает retry миграций (`DB_WAIT_MAX_ATTEMPTS`, `DB_WAIT_SLEEP_SECONDS`).
- Локально:
  - Применить: `alembic upgrade head`
  - Откат на 1 шаг: `alembic downgrade -1`
  - Создать ревизию: `alembic revision -m "your_change"`

### Existing external DB
Если у вас уже есть PostgreSQL, укажите внешний `DATABASE_URL` в `.env` (например, хост managed БД).
В этом режиме backend подключится к внешней БД, а встроенный контейнер `postgres` можно не использовать.

## Test Mission Assets
- Примеры CRM payload для ручной проверки лежат в `mock.json`.

## Security and Maintainability
- Конфигурация и секреты через env, без hardcode.
- Строгие Pydantic-схемы для входа/выхода.
- OOP/SOLID разбиение на слои: API / services / repositories / domain.
