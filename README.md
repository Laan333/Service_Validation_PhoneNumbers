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

## API (метрики и dev)

### `GET /api/v1/metrics/summary`
Возвращает total/valid/invalid/success_rate и breakdown причин отказа.

### `GET /api/v1/metrics/timeseries?days=7`
Возвращает динамику по дням за период.

### `GET /api/v1/metrics/recent?limit=20`
Возвращает последние обработанные лиды для таблицы на дашборде.

### `GET /api/v1/dev/mock-leads` (только для дашборда / replay)
Возвращает JSON `{"items": [...], "source_path": "<абсолютный путь>"}`. Список лидов читается из **`mock.json`** в корне репозитория (локально) или из **`/app/mock.json`** в Docker (файл монтируется из `./mock.json`). Путь к файлу **не** настраивается через `.env`.

---

## CRM Webhook: `POST /api/v1/webhooks/crm/lead`

Единственная точка приёма лида из CRM. Сохраняет результат валидации в БД и возвращает итог наружу.

### Базовые URL

| Окружение | URL |
|-----------|-----|
| Docker Compose (через Nginx) | `http://localhost:8005/api/v1/webhooks/crm/lead` |
| Прямой backend (без Nginx) | `http://localhost:8000/api/v1/webhooks/crm/lead` |

Метод: **`POST`**. Тело: **JSON** (`Content-Type: application/json`).

### Аутентификация (опционально)

Если в `.env` задан **`WEBHOOK_TOKEN`**, клиент **обязан** передать заголовок:

```http
X-Webhook-Token: <то же значение, что WEBHOOK_TOKEN>
```

Если `WEBHOOK_TOKEN` пустой или не задан, заголовок не проверяется (удобно для локальной разработки).

### Форматы тела запроса

Поддерживаются **два** варианта (после нормализации оба превращаются в одну плоскую модель с полями Bitrix).

**1. Плоский объект** (как строки в корневом массиве `mock.json`):

```json
{
  "ID": "190301",
  "TITLE": "New deal from James Carter",
  "STAGE_ID": "NEW",
  "CURRENCY_ID": "USD",
  "CONTACT_ID": "821001",
  "CONTACT_NAME": "James Carter",
  "CONTACT_EMAIL": "james@example.com",
  "CONTACT_PHONE": "(714) 883-9188",
  "SOURCE_ID": "WEB",
  "COMMENTS": "многострочный текст с \\n допускается",
  "UTM_SOURCE": "google",
  "UTM_MEDIUM": "cpc",
  "UTM_CAMPAIGN": "{01_Performance_Elementary_tCPA}",
  "UTM_CONTENT": "{Elementary}",
  "DATE_CREATE": "2026-01-05T10:12:00+03:00"
}
```

**2. Обёртка Bitrix** (`FIELDS` — объект или JSON-строка с объектом):

```json
{
  "FIELDS": {
    "ID": "190301",
    "CONTACT_PHONE": "+12025551234",
    "TITLE": "Deal"
  }
}
```

или вложенно:

```json
{
  "event": "ONCRMLEADADD",
  "data": {
    "FIELDS": "{\"ID\":\"190301\",\"CONTACT_PHONE\":\"4155552671\"}"
  }
}
```

Неизвестные ключи на верхнем уровне плоского объекта **игнорируются** (`extra="ignore"` в Pydantic).

### Поля (имена как в CRM)

| JSON-ключ | Назначение | Обязательность |
|-----------|------------|----------------|
| `ID` | Идентификатор лида/сделки | **Да** (после приведения к строке допускается число в JSON) |
| `CONTACT_PHONE` | Сырой телефон | Нет; пустая строка эквивалентна отсутствию номера |
| `TITLE`, `STAGE_ID`, `CURRENCY_ID`, `CONTACT_ID`, `CONTACT_NAME`, `CONTACT_EMAIL`, `SOURCE_ID`, `COMMENTS`, `UTM_*`, `DATE_CREATE` | Метаданные / UTM / комментарий | Нет; используются для совместимости с реальным webhook |

Логика нормализации использует в первую очередь **`ID`** и **`CONTACT_PHONE`**.

### Успешный ответ `200 OK`

```json
{
  "lead_id": "190301",
  "status": "valid",
  "normalized_phone": "+17148839188",
  "reason": null,
  "source": "deterministic"
}
```

- `status`: `"valid"` или `"invalid"` (строго в нижнем регистре).
- `normalized_phone`: E.164 с `+` при успехе, иначе `null`.
- `reason`: машинный код отказа при `invalid`, иначе `null` (см. доменные enum’ы в `app/domain/enums.py`).
- `source`: `"deterministic"` или `"llm"` — какой путь дал итог.

### Ошибки

| Код | Когда |
|-----|--------|
| `401` | Задан `WEBHOOK_TOKEN`, но заголовок `X-Webhook-Token` отсутствует или неверен. |
| `422` | Невалидный JSON или тело не укладывается в схему после разворачивания `FIELDS` (детали в `detail` от FastAPI/Pydantic). |

### Примеры вызова

**curl (bash / Git Bash), без токена:**

```bash
curl -sS -X POST "http://localhost:8005/api/v1/webhooks/crm/lead" \
  -H "Content-Type: application/json" \
  -d "{\"ID\":\"190301\",\"TITLE\":\"Test\",\"CONTACT_PHONE\":\"(714) 883-9188\"}"
```

**PowerShell:**

```powershell
$body = '{"ID":"190301","TITLE":"Test","CONTACT_PHONE":"(714) 883-9188"}'
Invoke-RestMethod -Uri "http://localhost:8005/api/v1/webhooks/crm/lead" -Method Post -ContentType "application/json" -Body $body
```

**С токеном:**

```bash
curl -sS -X POST "http://localhost:8005/api/v1/webhooks/crm/lead" \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Token: your_secret" \
  -d "{\"ID\":\"1\",\"CONTACT_PHONE\":\"4155552671\"}"
```

### Как протестировать вебхук

1. **Автотесты (рекомендуется)** — тела запросов зашиты в коде тестов, `.env` для `mock.json` не нужен:
   ```bash
   pip install -e ".[dev]"
   pytest tests/integration/test_webhook.py tests/unit/test_crm_payload.py -q
   ```
   Покрыто: плоское тело, полный Bitrix-набор полей, обёртка `FIELDS`, проверка `401` при включённом `WEBHOOK_TOKEN`.

2. **Живой стек Docker** — поднимите `docker-compose up --build`, затем выполните один из `curl` / `Invoke-RestMethod` выше против `http://localhost:8005/...`. Убедитесь, что `WEBHOOK_TOKEN` в `.env` совпадает с заголовком (или оставьте токен пустым).

3. **Дашборд Mock Replay** — на `http://localhost:8005` блок **Mock Replay**: загружает лиды из **`mock.json`** (через `GET /api/v1/dev/mock-leads`) и по очереди шлёт **тот же JSON** на `POST .../webhooks/crm/lead`. Это эквивалентно ручному вызову вебхука для каждой записи в файле.

Работоспособность вебхука в репозитории обеспечивается указанными тестами; при изменении схемы тела запускайте `pytest` перед деплоем.

---

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
- Весь backend: `pytest`
- Вебхук и нормализация CRM JSON: `pytest tests/integration/test_webhook.py tests/unit/test_crm_payload.py`

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

## Файл `mock.json`

- В корне репозитория: массив объектов лида в формате Bitrix (те же ключи, что в примере вебхука выше), либо поддерживаемые обёртки (`items` / `leads` / `data` — см. `app/utils/crm_payload.py`).
- В Docker: `./mock.json` монтируется в контейнер как **`/app/mock.json`** (`read-only`). Backend ищет файл по пути рядом с пакетом `app` или по `/app/mock.json`. **Переменных окружения для пути к моку нет.**
- Дашборд **Mock Replay** и `GET /api/v1/dev/mock-leads` используют только этот файл.

## Security and Maintainability
- Конфигурация и секреты через env, без hardcode.
- Строгие Pydantic-схемы для входа/выхода.
- OOP/SOLID разбиение на слои: API / services / repositories / domain.
