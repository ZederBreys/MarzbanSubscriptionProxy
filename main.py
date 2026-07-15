import json
import logging
import base64
import re
import os
import sqlite3
import time
import threading
from urllib.parse import parse_qs, unquote
from logging.handlers import RotatingFileHandler
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, HTTPException
import httpx
from datetime import datetime
from typing import Dict, Optional

# ========== КОНФИГУРАЦИЯ ==========
TARGET_SERVICE_URL = "http://127.0.0.1:8000"
PROXY_PORT = 8089
CONFIG_DIR = "configs"
DB_PATH = "subscriptions.db"
CACHE_TTL = 30  # секунд жизни кэша перед автообновлением из БД

# ========== НАСТРОЙКА ЛОГГЕРОВ ==========
logging.basicConfig(level=logging.INFO)
req_logger = logging.getLogger("requests")
resp_logger = logging.getLogger("responses")

req_handler = RotatingFileHandler("requests.log", maxBytes=10_000_000, backupCount=5)
resp_handler = RotatingFileHandler("responses.log", maxBytes=10_000_000, backupCount=5)

req_handler.setFormatter(logging.Formatter('%(asctime)s\n%(message)s\n' + '-'*80))
resp_handler.setFormatter(logging.Formatter('%(asctime)s\n%(message)s\n' + '-'*80))

req_logger.addHandler(req_handler)
resp_logger.addHandler(resp_handler)

# ========== ГЛОБАЛЬНЫЙ КЭШ ==========
config_cache: Dict[str, str] = {}
subscription_cache: Dict[str, dict] = {}  # КЭШ ДАННЫХ ИЗ БД
cache_lock = threading.Lock()
last_db_load = 0

def load_configs_from_dir():
    """Загружает все JSON-файлы из CONFIG_DIR в память."""
    global config_cache
    new_cache = {}
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        example_path = os.path.join(CONFIG_DIR, "default.json")
        if not os.path.exists(example_path):
            with open(example_path, "w") as f:
                json.dump({"example": "put your full config here"}, f, indent=2)
            logging.warning(f"Created example config at {example_path}. Please edit it.")

    for filename in os.listdir(CONFIG_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(CONFIG_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    json.loads(content)   # валидация
                    name = filename[:-5]
                    new_cache[name] = content
                    logging.info(f"Loaded config: {name}")
            except Exception as e:
                logging.error(f"Failed to load {filename}: {e}")
    config_cache = new_cache
    logging.info(f"Total configs loaded: {len(config_cache)}")

def init_db():
    """Создаёт таблицу в БД, если её ещё нет."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS subscription_url (
                sud_id TEXT NOT NULL UNIQUE,
                config TEXT NOT NULL,
                profile_title TEXT,
                profile_update_interval INTEGER DEFAULT 12
            )
        ''')
    logging.info("Database initialized.")

def load_all_subscriptions_from_db():
    """Загружает ВСЕ записи из БД в кэш за один запрос."""
    global subscription_cache, last_db_load
    new_cache = {}
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT sud_id, config, profile_title, profile_update_interval FROM subscription_url")
            for row in cursor.fetchall():
                new_cache[row[0]] = {
                    "config": row[1],
                    "profile_title": row[2],
                    "profile_update_interval": row[3] if row[3] is not None else 12
                }
    except Exception as e:
        logging.error(f"Failed to load subscriptions from DB: {e}")
        return

    with cache_lock:
        subscription_cache = new_cache
        last_db_load = time.time()

    logging.info(f"Loaded {len(subscription_cache)} subscriptions from DB")

def get_subscription_config(sub_id: str) -> Optional[dict]:
    """Мгновенный поиск в кэше (O(1)). При необходимости автообновляет кэш из БД."""
    # Проверяем, не пора ли обновить кэш (каждые CACHE_TTL секунд)
    if time.time() - last_db_load > CACHE_TTL:
        load_all_subscriptions_from_db()
    
    with cache_lock:
        return subscription_cache.get(sub_id)

# ========== ПАРСИНГ VLESS ССЫЛКИ ==========
def parse_vless_url(url: str) -> Dict[str, str]:
    """
    Парсит VLESS ссылку вида:
    vless://UUID@SERVER:PORT?param1=value1&... #fragment
    Возвращает словарь параметров.
    """
    if not url.startswith("vless://"):
        raise ValueError("Not a vless URL")

    # Убираем префикс vless://
    without_proto = url[8:]

    # Разделяем на часть до '#' (фрагмент) и после
    fragment = ""
    if "#" in without_proto:
        without_proto, fragment = without_proto.split("#", 1)

    # Разделяем на часть до '?' (UUID@host:port) и параметры
    params_part = ""
    if "?" in without_proto:
        without_proto, params_part = without_proto.split("?", 1)

    # Извлекаем UUID@host:port
    uuid_host_port = without_proto
    if "@" not in uuid_host_port:
        raise ValueError("Missing @ in vless URL")
    uuid, host_port = uuid_host_port.split("@", 1)

    # Извлекаем host и port
    if ":" not in host_port:
        host = host_port
        port = ""
    else:
        host, port = host_port.split(":", 1)

    # Парсим query параметры
    query = {}
    if params_part:
        parsed_qs = parse_qs(params_part)
        query = {k: v[0] for k, v in parsed_qs.items()}

    # Декодируем и парсим статус подписки из fragment
    fragment_decoded = unquote(fragment) if fragment else ""
    subscription_status_emoji = ""
    subscription_status_text = ""
    subscription_status = ""
    if "✅" in fragment_decoded:
        subscription_status = "1"
        subscription_status_text = "Active"
        subscription_status_emoji = "✅"
    elif "❌" in fragment_decoded:
        subscription_status = "0"
        subscription_status_text = "Expired"
        subscription_status_emoji = "❌"

    result = {
        "XRAY_ID": uuid,
        "SERVER_IP": host,
        "SERVER_PORT": port,
        "FRAGMENT": fragment_decoded,
        "SUBSCRIPTION_STATUS": subscription_status,
        "SUBSCRIPTION_STATUS_TEXT": subscription_status_text,
        "SUBSCRIPTION_STATUS_EMOJI": subscription_status_emoji,
        **query   # все параметры из query переходят в результат
    }

    # Приводим часто используемые параметры к удобным именам
    if "pbk" in query:
        result["PUBLIC_KEY"] = query["pbk"]
    if "sid" in query:
        result["SHORT_ID"] = query["sid"]
    if "sni" in query:
        result["SNI"] = query["sni"]
    if "fp" in query:
        result["FP"] = query["fp"]
    if "flow" in query:
        result["FLOW"] = query["flow"]
    if "security" in query:
        result["SECURITY"] = query["security"]
    if "type" in query:
        result["TYPE"] = query["type"]
    if "headerType" in query:
        result["HEADER_TYPE"] = query["headerType"]
    if "path" in query:
        result["PATH"] = query["path"]
    if "host" in query:
        result["HOST"] = query["host"]
    if "allowInsecure" in query:
        result["ALLOW_INSECURE"] = query["allowInsecure"]

    return result

def apply_template(template: str, values: Dict[str, str]) -> str:
    """Заменяет все {{KEY}} в шаблоне на значения из словаря."""
    for key, val in values.items():
        template = template.replace(f"{{{{{key}}}}}", str(val))
    return template

# ========== ФУНКЦИИ ДЛЯ PROFILE-TITLE ==========
def decode_profile_title(encoded: str) -> str:
    if encoded.startswith("base64:"):
        b64_data = encoded[7:]
        try:
            return base64.b64decode(b64_data).decode('utf-8')
        except:
            return encoded
    return encoded

def encode_profile_title(text: str) -> str:
    b64_data = base64.b64encode(text.encode('utf-8')).decode('utf-8')
    return f"base64:{b64_data}"

# ========== СОЗДАНИЕ FASTAPI ПРИЛОЖЕНИЯ ==========
app = FastAPI()

# ========== LIFESPAN ДЛЯ HTTP КЛИЕНТА ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация БД, загрузка конфигов и кэша подписок
    init_db()
    load_configs_from_dir()
    load_all_subscriptions_from_db()
    app.state.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True, verify=False)
    yield
    await app.state.client.aclose()

app.router.lifespan_context = lifespan

# ========== ОСНОВНОЙ ПРОКСИ ==========
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy(request: Request, path: str):
    full_path = f"/{path}" if path else "/"
    body_bytes = await request.body()

    # Логируем запрос
    req_data = {
        "time": datetime.now().isoformat(),
        "method": request.method,
        "path": full_path,
        "query": str(request.query_params),
        "headers": dict(request.headers),
        "body": body_bytes.decode('utf-8', errors='replace')[:5000] if body_bytes else ""
    }
    req_logger.info(json.dumps(req_data, indent=2, ensure_ascii=False))
    logging.info(f"📥 {request.method} {full_path}")

    target_url = f"{TARGET_SERVICE_URL}{full_path}"
    if request.query_params:
        target_url += f"?{request.query_params}"

    try:
        resp = await app.state.client.request(
            method=request.method,
            url=target_url,
            headers={k: v for k, v in request.headers.items() if k.lower() not in ['host', 'content-length']},
            content=body_bytes if body_bytes else None,
        )

        # Логируем исходный ответ
        resp_logger.info(json.dumps({
            "time": datetime.now().isoformat(),
            "status": resp.status_code,
            "headers": dict(resp.headers),
            "body": resp.text[:5000] if resp.text else ""
        }, indent=2, ensure_ascii=False))
        logging.info(f"📤 {resp.status_code} (оригинал)")

        # Пропускаем HTML-ответы (панель администрирования)
        content_type = resp.headers.get("content-type", "")
        is_html_response = "text/html" in content_type

        # Модификация только для GET /sub/* (кроме HTML)
        if request.method == "GET" and re.match(r'^/sub/', full_path) and not is_html_response:
            logging.info(f"🔧 Обработка подписки для {full_path}")

            # 1. Извлекаем VLESS-ссылку из тела ответа
            original_body = resp.text.strip()
            if not original_body:
                error_body = json.dumps({"error": "Empty body from upstream"})
                return Response(content=error_body, status_code=500, media_type="application/json")

            # Если тело закодировано в base64 – пробуем декодировать
            try:
                if re.match(r'^[A-Za-z0-9+/=]+$', original_body):
                    decoded = base64.b64decode(original_body).decode('utf-8')
                    if decoded.startswith("vless://"):
                        original_body = decoded
                        logging.debug("🔓 Тело было в base64, декодировано.")
            except Exception:
                pass

            if not original_body.startswith("vless://"):
                logging.warning("⚠️ Тело ответа не является VLESS-ссылкой. Отдаём шаблон без замены.")
                vless_params = {}
            else:
                try:
                    vless_params = parse_vless_url(original_body)
                    logging.debug(f"✅ Распарсена VLESS-ссылка: {vless_params}")
                except Exception as e:
                    logging.error(f"❌ Ошибка парсинга VLESS: {e}")
                    vless_params = {}

            # 2. Получаем profile-web-page-url, извлекаем sub_id
            profile_web_page_url = resp.headers.get("profile-web-page-url", "")
            sub_id = None
            if profile_web_page_url:
                match = re.search(r'/sub/([^/?#]+)', profile_web_page_url)
                if match:
                    sub_id = match.group(1)
                    logging.debug(f"🆔 Найден sub_id: {sub_id}")

            # 3. МГНОВЕННЫЙ поиск в кэше памяти (без обращения к БД!)
            config_name = "default"
            custom_title = "🚀ZederBreys Family🌐"
            update_interval = None

            if sub_id:
                sub_config = get_subscription_config(sub_id)  # O(1) из словаря в памяти
                if sub_config:
                    raw_config = sub_config["config"]
                    if raw_config.endswith(".json"):
                        raw_config = raw_config[:-5]
                    if raw_config in config_cache:
                        config_name = raw_config
                    else:
                        logging.warning(f"⚠️ Конфиг '{raw_config}' не найден в кэше, использую default")
                    
                    if sub_config["profile_title"]:
                        custom_title = sub_config["profile_title"]
                    update_interval = sub_config["profile_update_interval"]
                    logging.debug(f"💾 Из кэша: config={config_name}, title={custom_title}, interval={update_interval}")
                else:
                    logging.info(f"ℹ️ sub_id '{sub_id}' отсутствует в БД, используются значения по умолчанию.")
            else:
                logging.info("ℹ️ Заголовок profile-web-page-url не содержит sub_id, используются значения по умолчанию.")

            # 4. Выбираем шаблон и подставляем параметры
            if config_name not in config_cache:
                config_name = "default"
            template = config_cache[config_name]

            if vless_params:
                new_body = apply_template(template, vless_params)
            else:
                new_body = template

            # 5. Формируем новые заголовки
            new_headers = dict(resp.headers)
            new_headers['profile-title'] = encode_profile_title(custom_title)
            if update_interval is not None:
                new_headers['profile-update-interval'] = str(update_interval)
            new_headers['content-length'] = str(len(new_body.encode('utf-8')))
            new_headers['content-type'] = 'application/json'

            logging.info(f"✨ Ответ заменён. Конфиг: {config_name}, Title: {custom_title}")
            return Response(content=new_body, status_code=resp.status_code, headers=new_headers)
        else:
            return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))

    except Exception as e:
        error_msg = f"❌ Ошибка: {type(e).__name__}: {e}"
        logging.error(error_msg, exc_info=True)
        req_logger.error(error_msg)
        return Response(
            content=json.dumps({"error": "Internal proxy error"}),
            status_code=502,
            media_type="application/json",
        )

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print("✅ ПРОКСИ С КЭШИРОВАНИЕМ В ПАМЯТИ (0 задержек от БД)")
    print(f"📍 Порт: {PROXY_PORT}")
    print(f"📁 Конфиги: {CONFIG_DIR}/*.json")
    print(f"🗄️  База данных: {DB_PATH}")
    print(f"⏱️  Автообновление кэша каждые {CACHE_TTL} сек")
    print(f"🔄 Перезагрузка: POST /admin/reload-configs")
    print("="*60)
    uvicorn.run(app, host="0.0.0.0", port=PROXY_PORT, log_level="info")