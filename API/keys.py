"""Optional proxy keys loaded from an operator-managed private JSON file."""

import hashlib
import hmac
import json
import os
from pathlib import Path

from fastapi import HTTPException


def keys_path():
    return Path(os.environ.get("LEOAI_KEYS_FILE", Path(__file__).with_name("keys.json")))


def lookup_key(key):
    try:
        data = json.loads(keys_path().read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        raise HTTPException(503, "API key configuration unavailable") from None
    if (not isinstance(data, dict) or not isinstance(data.get("keys"), list)
            or any(not isinstance(value, str) or not 32 <= len(value) <= 256
                   or not value.isascii() or any(c.isspace() for c in value)
                   for value in data["keys"])):
        raise HTTPException(503, "API key configuration unavailable")
    supplied = hashlib.sha256(key.encode("utf-8")).digest()
    matched = False
    for configured in data["keys"]:
        matched |= hmac.compare_digest(supplied, hashlib.sha256(configured.encode("utf-8")).digest())
    return (supplied.hex(),) if matched else None
