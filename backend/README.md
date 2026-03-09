# Backend: выдача API-ключа

Скрипт `api.php` отдаёт значение `OPENAI_API_KEY` из `.env` в формате JSON: `{"api_key": "sk-..."}`.

## Установка

1. Скопируйте `.env.example` в `.env`.
2. В `.env` укажите:
   - `OPENAI_API_KEY=sk-...` — ваш ключ OpenAI.
   - `API_TOKEN=...` (опционально) — секрет для доступа. Если задан, запрос без правильного токена получит 403.

## Запрос ключа

- **Без токена:** `GET https://your-domain.com/backend/api.php` (если в .env не задан API_TOKEN).
- **С токеном:** `GET https://your-domain.com/backend/api.php?token=ЗНАЧЕНИЕ_ИЗ_API_TOKEN` или заголовок `X-Token: ЗНАЧЕНИЕ_ИЗ_API_TOKEN`.

## exam_core.py

Задайте URL backend (в окружении или в коде):
- `EXAM_BACKEND_KEY_URL=https://lan.avto-glass.kz/kmu.php`

Если в .env на сервере задан **API_TOKEN**, то в окружении при запуске ноутбука задайте тот же секрет:
- `EXAM_BACKEND_TOKEN=то_же_значение_что_и_API_TOKEN`
Тогда exam_core будет отправлять его в заголовке X-Token.

Либо измените константу `BACKEND_KEY_URL` в `exam_core.py`.
