"""Shared helper utilities for formatting responses and loading JSON data."""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import Path, Query, HTTPException
from pydantic import UUID4
from app.services.logger.logger import get_logger

logger = get_logger(__name__)


def generate_traceback_id() -> str:
    """Generate a unique traceback identifier for response payloads."""
    return str(uuid.uuid4())


def format_response(
    *,
    detail_type=None,
    data=None,
    loc=None,
    msg=None,
    input_value=None,
    reason=None,
    status_code=None,
    pagination: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Format standardized success response."""
    response = {
        "detail": [{
            "detail_type": detail_type,
            "traceback_id": generate_traceback_id(),
            "msg": msg,
            "data": data if data is not None else {}
        }]
    }
    if pagination is not None:
        response["pagination"] = pagination
    return response


def exception_format_response(
    *,
    detail_type=None,
    data=None,
    loc=None,
    msg=None,
    input_value=None,
    reason=None,
) -> Dict[str, Any]:
    """Format standardized error response."""
    payload = {
        "detail_type": detail_type,
        "traceback_id": generate_traceback_id(),
        "msg": msg,
    }
    if reason:
        payload["ctx"] = {"reason": reason}
    return payload


def load_message_details(file_path: str) -> dict:
    """Load message details from a JSON file."""
    logger.debug("Loading message details from file_path=%s", file_path)
    with open(file_path, "r") as file:
        data = json.load(file)
    logger.debug("Loaded message detail keys=%s", len(data))
    return data


def serialize_datetime(obj):
    """Serialize datetime to ISO 8601 string."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")


def parse_optional_uuid_path(model_id: str = Path(...)) -> Optional[UUID4]:
    """Allow optional UUID in path, even if passed as 'null' or empty."""
    if model_id in ("", "null", "None", "undefined"):
        return None
    try:
        return UUID4(model_id)
    except ValueError:
        logger.warning("Invalid UUID path parameter model_id=%s", model_id)
        raise HTTPException(status_code=422, detail="Invalid UUID format (path parameter)")


def parse_optional_uuid_query(model_id: Optional[str] = Query(None)) -> Optional[UUID4]:
    """Parse UUID from a query parameter, return None if not provided or 'null'."""
    if model_id in (None, "", "null", "None", "undefined"):
        return None
    try:
        return UUID4(model_id)
    except ValueError:
        logger.warning("Invalid UUID query parameter model_id=%s", model_id)
        raise HTTPException(status_code=422, detail="Invalid UUID format (query parameter)")
