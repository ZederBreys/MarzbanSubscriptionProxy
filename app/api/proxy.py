import json
import logging
import base64
import re
from datetime import datetime

from fastapi import APIRouter, Request, Response

from app.core.config import TARGET_SERVICE_URL
from app.core.logging_setup import req_logger, resp_logger
from app.services.cache_service import config_cache
from app.services.subscription_service import get_subscription_config
from app.utils.vless import parse_vless_url
from app.utils.template import apply_template, encode_profile_title

proxy_router = APIRouter(include_in_schema=False)


@proxy_router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
)
async def proxy(request: Request, path: str) -> Response:
    full_path = f"/{path}" if path else "/"
    body_bytes = await request.body()

    req_data = {
        "time": datetime.now().isoformat(),
        "method": request.method,
        "path": full_path,
        "query": str(request.query_params),
        "headers": dict(request.headers),
        "body": body_bytes.decode("utf-8", errors="replace")[:5000] if body_bytes else "",
    }
    req_logger.info(json.dumps(req_data, indent=2, ensure_ascii=False))
    logging.info(f"📥 {request.method} {full_path}")

    target_url = f"{TARGET_SERVICE_URL}{full_path}"
    if request.query_params:
        target_url += f"?{request.query_params}"

    try:
        resp = await request.app.state.client.request(
            method=request.method,
            url=target_url,
            headers={
                k: v
                for k, v in request.headers.items()
                if k.lower() not in ["host", "content-length"]
            },
            content=body_bytes if body_bytes else None,
        )

        resp_logger.info(
            json.dumps(
                {
                    "time": datetime.now().isoformat(),
                    "status": resp.status_code,
                    "headers": dict(resp.headers),
                    "body": resp.text[:5000] if resp.text else "",
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        logging.info(f"📤 {resp.status_code} (оригинал)")

        content_type = resp.headers.get("content-type", "")
        is_html_response = "text/html" in content_type

        if request.method == "GET" and re.match(r"^/sub/", full_path) and not is_html_response:
            logging.info(f"🔧 Обработка подписки для {full_path}")

            original_body = resp.text.strip()
            if not original_body:
                error_body = json.dumps({"error": "Empty body from upstream"})
                return Response(content=error_body, status_code=500, media_type="application/json")

            try:
                if re.match(r"^[A-Za-z0-9+/=]+$", original_body):
                    decoded = base64.b64decode(original_body).decode("utf-8")
                    if decoded.startswith("vless://"):
                        original_body = decoded
                        logging.debug("🔓 Тело было в base64, декодировано.")
            except Exception:
                pass

            if not original_body.startswith("vless://"):
                logging.warning("⚠️ Тело ответа не является VLESS-ссылкой. Отдаём шаблон без замены.")
                vless_params: dict[str, str] = {}
            else:
                try:
                    vless_params = parse_vless_url(original_body)
                    logging.debug(f"✅ Распарсена VLESS-ссылка: {vless_params}")
                except Exception as e:
                    logging.error(f"❌ Ошибка парсинга VLESS: {e}")
                    vless_params = {}

            profile_web_page_url = resp.headers.get("profile-web-page-url", "")
            sub_id = None
            if profile_web_page_url:
                match = re.search(r"/sub/([^/?#]+)", profile_web_page_url)
                if match:
                    raw_sub_id = match.group(1)
                    try:
                        padding = 4 - len(raw_sub_id) % 4
                        if padding != 4:
                            raw_sub_id += "=" * padding
                        sub_id_bytes = base64.urlsafe_b64decode(raw_sub_id)
                        sub_id = sub_id_bytes.decode("utf-8", errors="replace").split(",", 1)[0]
                        logging.info(f"✅ sub_id успешно: {sub_id}")
                    except Exception as e:
                        logging.warning(f"Не удалось декодировать sub_id: {str(e)}")
                        # fallback
                        sub_id = raw_sub_id.split(",", 1)[0]
                else:
                    sub_id = None
            else:
                sub_id = None

            logging.debug(f"🆔 Найден sub_id: {sub_id}")

            config_name = "default"
            custom_title = "🚀ZederBreys Family🌐"
            update_interval = None

            if sub_id:
                sub_config = get_subscription_config(sub_id)
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

            if config_name not in config_cache:
                config_name = "default"
            template = config_cache[config_name]

            if vless_params:
                new_body = apply_template(template, vless_params)
            else:
                new_body = template

            new_headers = dict(resp.headers)
            new_headers["profile-title"] = encode_profile_title(custom_title)
            if update_interval is not None:
                new_headers["profile-update-interval"] = str(update_interval)
            new_headers["content-length"] = str(len(new_body.encode("utf-8")))
            new_headers["content-type"] = "application/json"

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
