# Marzban Subscription Proxy

Прозрачный прокси-сервер для модификации VLESS-подписок Marzban.

Перехватывает ответы на подписки (`/sub/*`), парсит VLESS-ссылку, подставляет её параметры в кастомный XRay JSON-шаблон и возвращает клиенту готовую конфигурацию. Включает веб-панель администратора для управления конфигами, пользователями, логами и аудитом.

## Как это работает

```
Пользователь
    ↓
Caddy (или другой reverse proxy)
    ↓
Marzban Subscription Proxy  ←—— этот проект
    ↓
Marzban API
    ↓
Xray
```

Marzban отдаёт клиенту VLESS-ссылку при запросе подписки. Прокси перехватывает ответ, парсит VLESS-ссылку, подставляет её параметры в JSON-шаблон (`configs/*.json`) и возвращает готовый XRay-конфиг с нужными маршрутами и настройками.

## Возможности

- Полная прозрачность для Marzban — прокси не меняет запросы и ответы для остальных эндпоинтов
- Модификация только GET-запросов на `/sub/*` (подписки), HTML-ответы панели не затрагиваются
- Автоматическое определение статуса подписки (`✅`/`❌`) из fragment VLESS-ссылки
- In-memory кэширование подписок и конфигов — без задержек на БД при каждом запросе
- Автоматическое обновление кэша из SQLite через заданный интервал
- Поддержка нескольких пользователей с разными конфигами (через SQLite)
- Base64-decode тела подписки (Marzban иногда кодирует ответ)
- Кастомный `profile-title` и `profile-update-interval` для подписок
- Веб-панель администратора:
  - управление XRay JSON-конфигами (создание, клонирование, редактирование в Monaco, удаление)
  - управление пользователями (создание, редактирование, удаление)
  - массовые операции: глобальная замена DNS-серверов и управление domain-списками
  - просмотр логов (requests / responses / application)
  - журнал аудита административных действий
- Аутентификация администраторов (cookie-сессии, argon2, CSRF-защита, защита от брутфорса)

## Стек

- **Python 3.11+**
- **FastAPI** — HTTP-сервер
- **httpx** — асинхронный HTTP-клиент для проксирования
- **SQLite3** — хранение привязок пользователей к конфигам, администраторов, сессий и аудита
- **Uvicorn** — ASGI-сервер
- **argon2-cffi** — хеширование паролей администраторов

## Структура проекта

```
.
├── main.py                     # Точка входа: инициализация, lifespan, запуск uvicorn
├── app/
│   ├── api/
│   │   ├── proxy.py            # Прозрачное проксирование и обработка /sub/*
│   │   └── admin/              # API админ-панели (auth, users, configs, logs, bulk, audit, settings)
│   ├── core/                   # Конфигурация, безопасность, аутентификация, логирование
│   ├── database/               # Подключение к SQLite, схемы и запросы
│   ├── middleware/             # CSRF-защита и security-заголовки
│   ├── services/               # Бизнес-логика (подписки, конфиги, auth, bulk, audit, logs)
│   └── utils/                  # Парсер VLESS и подстановка в шаблон
├── frontend/                   # Веб-панель администратора (HTML/CSS/JS + Monaco)
├── configs/                    # XRay JSON-шаблоны с {{PLACEHOLDER}}
│   └── default.json            #   Шаблон по умолчанию (системный, не удаляется)
├── requirements.txt            # Зависимости Python
├── .env.example                # Пример переменных окружения
└── README.md
```

База данных (`subscriptions.db`) и логи (`*.log`) создаются автоматически при первом запуске и не хранятся в git.

## Установка

### 1. Клонирование

```bash
git clone https://github.com/your-username/marzban-sub-proxy.git
cd marzban-sub-proxy
```

### 2. Виртуальное окружение

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows
```

### 3. Зависимости

```bash
pip install -r requirements.txt
```

### 4. Конфигурация

Скопируйте пример окружения и при необходимости задайте значения:

```bash
cp .env.example .env
```

Поддерживаемые переменные окружения (все необязательные):

| Переменная | По умолчанию | Описание |
|---|---|---|
| `TARGET_SERVICE_URL` | `http://127.0.0.1:8000` | Адрес Marzban API |
| `PROXY_PORT` | `8089` | Порт, на котором слушает прокси |
| `SECURE_COOKIES` | `false` | Флаг `Secure` для session-cookie (включать за HTTPS) |

### 5. Создание администратора

Перед первым входом в панель создайте учётную запись администратора:

```bash
python -m app.cli create-admin
```

Команда интерактивно запросит логин и пароль (пароль хранится только в виде argon2-хеша).

### 6. Запуск

```bash
python main.py
```

Сервер запустится на порту `8089`. Админ-панель доступна по адресу `http://127.0.0.1:8089/admin/panel/`.

Для публичного доступа настройте Caddy или nginx так, чтобы пробросить трафик с вашего домена на `localhost:8089`, и включите `SECURE_COOKIES=true`.

## Конфигурация

### Директория конфигов (`configs/`)

XRay JSON-шаблоны с плейсхолдерами `{{KEY}}`, которые заменяются на значения из VLESS-ссылки:

| Плейсхолдер | Источник в VLESS |
|---|---|
| `{{XRAY_ID}}` | UUID пользователя |
| `{{SERVER_IP}}` | IP сервера из VLESS |
| `{{SERVER_PORT}}` | Порт сервера |
| `{{PUBLIC_KEY}}` | Параметр `pbk` |
| `{{SHORT_ID}}` | Параметр `sid` |
| `{{SNI}}` | Параметр `sni` |
| `{{FP}}` | Параметр `fp` (fingerprint) |
| `{{FLOW}}` | Параметр `flow` |
| `{{SECURITY}}` | Параметр `security` |
| `{{TYPE}}` | Параметр `type` (network) |
| `{{HOST}}` | Параметр `host` |
| `{{PATH}}` | Параметр `path` |
| `{{FRAGMENT}}` | Фрагмент URL (#...) |
| `{{SUBSCRIPTION_STATUS}}` | Статус подписки: `1` (активна) или `0` (истекла) |
| `{{SUBSCRIPTION_STATUS_TEXT}}` | Текст статуса: `Active` или `Expired` |
| `{{SUBSCRIPTION_STATUS_EMOJI}}` | Эмодзи статуса: `✅` или `❌` |

`default.json` — системный конфиг: он всегда используется как fallback и не может быть удалён через панель.

## База данных

База данных SQLite используется для хранения привязок подписок к конфигурациям, учётных записей администраторов, активных сессий и журнала аудита. Файл `subscriptions.db` создаётся автоматически при первом запуске, обновляется через встроенные миграции и **не хранится в Git** (см. `.gitignore`).

### Таблицы

#### `subscription_url`

Привязка идентификатора подписки (`sud_id`) к JSON-конфигурации и настройкам профиля.

```sql
CREATE TABLE IF NOT EXISTS subscription_url (
    sud_id TEXT NOT NULL UNIQUE,
    config TEXT NOT NULL,
    profile_title TEXT,
    profile_update_interval INTEGER DEFAULT 12
);
```

- `sud_id` — уникальный идентификатор подписки (извлекается из заголовка `profile-web-page-url`).
- `config` — имя конфига из `configs/` без расширения; при отсутствии используется `default`.
- `profile_title` — кастомный заголовок профиля (опционально).
- `profile_update_interval` — интервал обновления подписки в часах (по умолчанию `12`).

#### `admin_users`

Учётные записи администраторов панели.

```sql
CREATE TABLE IF NOT EXISTS admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    last_login_at REAL,
    last_login_ip TEXT,
    created_at REAL DEFAULT (CAST(strftime('%s', 'now') AS REAL))
);
```

- `id` — первичный ключ.
- `login` — уникальный логин администратора.
- `password_hash` — argon2-хеш пароля (пароль в открытом виде не хранится).
- `last_login_at` / `last_login_ip` — время и IP последнего входа.
- `created_at` — время создания записи (unix timestamp).

#### `admin_sessions`

Активные cookie-сессии администраторов.

```sql
CREATE TABLE IF NOT EXISTS admin_sessions (
    session_hash TEXT PRIMARY KEY,
    admin_id INTEGER NOT NULL,
    ip_address TEXT NOT NULL DEFAULT '',
    csrf_token_hash TEXT NOT NULL DEFAULT '',
    expires_at REAL NOT NULL,
    last_accessed_at REAL DEFAULT (CAST(strftime('%s', 'now') AS REAL)),
    created_at REAL DEFAULT (CAST(strftime('%s', 'now') AS REAL)),
    FOREIGN KEY (admin_id) REFERENCES admin_users(id) ON DELETE CASCADE
);
```

- `session_hash` — хеш идентификатора сессии (первичный ключ); сам токен в БД не хранится.
- `admin_id` — внешний ключ на `admin_users.id`; при удалении администратора его сессии удаляются каскадно.
- `ip_address` — IP, с которого создана сессия.
- `csrf_token_hash` — хеш CSRF-токена, связанного с сессией.
- `expires_at` — время истечения сессии.

#### `admin_audit_log`

Журнал административных действий.

```sql
CREATE TABLE IF NOT EXISTS admin_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL DEFAULT (CAST(strftime('%s', 'now') AS REAL)),
    admin_login TEXT NOT NULL,
    ip_address TEXT,
    action TEXT NOT NULL,
    object_type TEXT NOT NULL,
    object_id TEXT,
    old_value_json TEXT,
    new_value_json TEXT,
    description TEXT,
    result TEXT NOT NULL DEFAULT 'SUCCESS'
);
```

- `id` — первичный ключ.
- `timestamp` — время события.
- `admin_login` — логин администратора, выполнившего действие.
- `action` / `object_type` / `object_id` — тип действия, тип и идентификатор затронутого объекта.
- `old_value_json` / `new_value_json` — JSON-снимки значения до и после изменения (при необходимости).
- `result` — результат операции (`SUCCESS` / `FAIL`).

### Связи

- `admin_sessions.admin_id → admin_users.id` (с каскадным удалением).
- `subscription_url.config` ссылается на имя файла в `configs/` (это не внешний ключ БД, а имя файла).
- `admin_audit_log.admin_login` хранит логин, а не внешний ключ, поэтому журнал сохраняется даже после удаления администратора.

### Миграции

Схема создаётся и обновляется автоматически при запуске приложения (`init_db()` в `app/database/connection.py`). Операторы `CREATE TABLE IF NOT EXISTS` идемпотентны, а миграции `ALTER TABLE ... ADD COLUMN` применяются безопасно (пропускаются, если колонка уже существует). `subscriptions.db` — локальный runtime-файл, который создаётся при первом запуске и не коммитится в репозиторий.

## Принцип работы

1. **GET-запрос** на `/sub/<id>` приходит в прокси
2. Прокси пересылает запрос в Marzban API (`TARGET_SERVICE_URL`)
3. Ответ Marzban содержит VLESS-ссылку (иногда в base64)
4. Прокси:
   - Декодирует base64 (если нужно)
   - Парсит VLESS-ссылку на составляющие (UUID, IP, параметры)
   - Извлекает `sub_id` из заголовка `profile-web-page-url`
   - Ищет привязку в кэше (или БД) — какой конфиг использовать
   - Подставляет значения из VLESS в JSON-шаблон
   - Определяет статус подписки из fragment (`✅`/`❌`) и добавляет `{{SUBSCRIPTION_STATUS_*}}`
   - Добавляет заголовки `profile-title` и `profile-update-interval`
5. **Ответ** — готовый XRay JSON-конфиг для импорта в клиент

Если пользователь не найден в БД или его конфиг отсутствует, используется `default`.

## Админ-панель

Панель доступна после входа (`/admin/auth/login`) и включает разделы:

- **Конфиги** — список, создание (пустой или клон существующего), редактирование в Monaco Editor с валидацией JSON, удаление
- **Пользователи** — список, создание, редактирование, удаление с опциональным удалением связанного конфига
- **Логи** — просмотр `requests.log`, `responses.log`, `app.log`
- **Массовые операции** — глобальная замена DNS-серверов, добавление/удаление domain-записей во всех конфигах
- **Аудит** — журнал административных действий
- **Профиль** — смена пароля

## Лицензия

[GPLv3](LICENSE)
