# Marzban Subscription Proxy

Прозрачный прокси-сервер для модификации VLESS-подписок Marzban.

Позволяет подменять конфигурацию XRay, которую получают клиенты, на кастомные JSON-шаблоны с автоматической подстановкой параметров из VLESS-ссылки.

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

Marzban отдаёт клиенту VLESS-ссылку при запросе подписки.  
Этот прокси перехватывает ответ, парсит VLESS-ссылку, подставляет её параметры в JSON-шаблон (`configs/*.json`) и возвращает готовый XRay-конфиг с нужными маршрутами и настройками.

## Возможности

- Полная прозрачность для Marzban — прокси не меняет запросы и ответы для остальных эндпоинтов
- Модификация только GET-запросов на `/sub/*` (подписки), HTML-ответы панели не затрагиваются
- Автоматическое определение статуса подписки (`✅`/`❌`) из fragment VLESS-ссылки
- In-memory кэширование подписок и конфигов — без задержек на БД при каждом запросе
- Автоматическое обновление кэша из SQLite каждые N секунд
- Поддержка нескольких пользователей с разными конфигами (через SQLite)
- Base64-decode тела подписки (Marzban иногда кодирует ответ)
- Логирование запросов и ответов в отдельные файлы с ротацией
- Кастомный `profile-title` и `profile-update-interval` для подписок

## Стек

- **Python 3.11+**
- **FastAPI** — HTTP-сервер
- **httpx** — асинхронный HTTP-клиент для проксирования
- **SQLite3** — хранение привязок пользователей к конфигам
- **Uvicorn** — ASGI-сервер

## Структура проекта

```
marzban_api/
├── main.py                 # Точка входа и вся логика приложения
├── configs/                # XRay JSON-шаблоны с {{PLACEHOLDER}} 
│   ├── default.json        #   Шаблон по умолчанию
│   ├── mypc.json           #   Шаблон для конкретного пользователя
│   └── ...
├── subscriptions.db        # SQLite-БД (создаётся автоматически, не в git)
├── requirements.txt        # Зависимости Python
├── .gitignore
├── .env.example            # Пример переменных окружения
└── README.md
```

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

### 4. Подготовка

Прокси создаёт БД и директорию конфигов автоматически при первом запуске.  
Достаточно запустить:

```bash
python main.py
```

При первом запуске будет создана `configs/default.json` — заполните её своими настройками.

### 5. Добавление пользователей в БД

Привязка пользователя к конфигу хранится в `subscriptions.db`.  
Вставьте запись вручную или через свой скрипт:

```sql
INSERT INTO subscription_url (sud_id, config, profile_title, profile_update_interval)
VALUES ('<sub_id_from_marzban>', 'mypc', '🚀 Мой ПК', 12);
```

- `sud_id` — идентификатор подписки из URL (берётся из заголовка `profile-web-page-url`)
- `config` — имя JSON-файла из `configs/` (без расширения `.json`)
- `profile_title` — название подписки (будет показано в клиенте)
- `profile_update_interval` — интервал обновления в часах

### 6. Запуск

```bash
python main.py
```

Сервер запустится на порту `8089` (меняется в `main.py`, константа `PROXY_PORT`).

Настройте Caddy или nginx пробросить трафик с вашего домена на `localhost:8089`.

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

### SQLite

База данных создаётся автоматически в файле `subscriptions.db`.  

Схема:

```sql
CREATE TABLE subscription_url (
    sud_id TEXT NOT NULL UNIQUE,
    config TEXT NOT NULL,
    profile_title TEXT,
    profile_update_interval INTEGER DEFAULT 12
);
```

### Основные настройки (в `main.py`)

| Константа | По умолчанию | Описание |
|---|---|---|
| `TARGET_SERVICE_URL` | `http://127.0.0.1:8000` | Адрес Marzban API |
| `PROXY_PORT` | `8089` | Порт, на котором слушает прокси |
| `CONFIG_DIR` | `configs` | Директория с JSON-шаблонами |
| `DB_PATH` | `subscriptions.db` | Путь к SQLite-БД |
| `CACHE_TTL` | `30` | Секунд между обновлениями кэша из БД |

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

## Лицензия

Предлагается **MIT License** — простая, разрешительная лицензия, позволяющая свободно использовать, модифицировать и распространять код как в закрытых, так и в открытых проектах. Совместима с приватным репозиторием на GitHub.
