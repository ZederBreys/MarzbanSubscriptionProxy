from typing import Dict
from urllib.parse import parse_qs, unquote


def parse_vless_url(url: str) -> Dict[str, str]:
    if not url.startswith("vless://"):
        raise ValueError("Not a vless URL")

    without_proto = url[8:]

    fragment = ""
    if "#" in without_proto:
        without_proto, fragment = without_proto.split("#", 1)

    params_part = ""
    if "?" in without_proto:
        without_proto, params_part = without_proto.split("?", 1)

    uuid_host_port = without_proto
    if "@" not in uuid_host_port:
        raise ValueError("Missing @ in vless URL")
    uuid, host_port = uuid_host_port.split("@", 1)

    if ":" not in host_port:
        host = host_port
        port = ""
    else:
        host, port = host_port.split(":", 1)

    query = {}
    if params_part:
        parsed_qs = parse_qs(params_part)
        query = {k: v[0] for k, v in parsed_qs.items()}

    fragment_decoded = unquote(fragment) if fragment else ""
    subscription_status_emoji = ""
    subscription_status_text = ""
    subscription_status = ""
    if "✅" in fragment_decoded:
        subscription_status = "1"
        subscription_status_text = ""
        subscription_status_emoji = ""
    elif "❌" in fragment_decoded:
        subscription_status = "0"
        subscription_status_text = " (Деактивирован)"
        subscription_status_emoji = "❌"

    result = {
        "XRAY_ID": uuid,
        "SERVER_IP": host,
        "SERVER_PORT": port,
        "FRAGMENT": fragment_decoded,
        "SUBSCRIPTION_STATUS": subscription_status,
        "SUBSCRIPTION_STATUS_TEXT": subscription_status_text,
        "SUBSCRIPTION_STATUS_EMOJI": subscription_status_emoji,
        **query,
    }

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
