import base64
from typing import Dict


def apply_template(template: str, values: Dict[str, str]) -> str:
    for key, val in values.items():
        template = template.replace(f"{{{{{key}}}}}", str(val))
    return template


def decode_profile_title(encoded: str) -> str:
    if encoded.startswith("base64:"):
        b64_data = encoded[7:]
        try:
            return base64.b64decode(b64_data).decode("utf-8")
        except Exception:
            return encoded
    return encoded


def encode_profile_title(text: str) -> str:
    b64_data = base64.b64encode(text.encode("utf-8")).decode("utf-8")
    return f"base64:{b64_data}"
