"""Shared source-envelope screening, independent of legacy fixture importers."""

import json

from ..contracts import CoreError

SECRET_NAMES = {'api_key','apikey','token','cookie','password','secret','authorization','credentials'}


def safe_payload(value):
    if isinstance(value, dict):
        if any(str(k).lower() in SECRET_NAMES for k in value):
            raise CoreError('SECRET_FIELD_IN_EXPORT')
        for child in value.values():
            safe_payload(child)
    elif isinstance(value, list):
        for child in value:
            safe_payload(child)
    elif isinstance(value, str) and value.lstrip().startswith(('{', '[')):
        try:
            decoded = json.loads(value)
        except ValueError:
            return
        safe_payload(decoded)
