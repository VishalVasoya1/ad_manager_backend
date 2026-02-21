"""Shared helper utilities for formatting responses and loading JSON data."""

import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import Path, Query, HTTPException
from pydantic import UUID4
from app.services.logger.logger import get_logger

logger = get_logger(__name__)


def format_response(
    detail_type=None,
    data=None,
    loc=None,
    msg=None,
    input_value=None,
    reason=None,
    status_code=None,
):
    """Formats a standardized success response with data and metadata separated."""
    return {
        "data": data,
        "meta": {
            "type": detail_type,
            "message": msg,
            "status_code": status_code,
            "traceback_id": str(uuid.uuid4()),
        }
    }


def exception_format_response(
    detail_type=None, data=None, loc=None, msg=None, input_value=None, reason=None
):
    """Formats a standardized error/exception response dictionary."""
    response_detail = {}
    if detail_type is not None:
        response_detail["type"] = detail_type
    if data is not None:
        response_detail["data"] = data
    if loc is not None:
        response_detail["loc"] = [loc]
    if msg is not None:
        response_detail["msg"] = msg
    if input_value is not None:
        response_detail["input"] = input_value
    if reason is not None:
        response_detail["ctx"] = {"reason": reason}
    response_detail["traceback_id"] = str(uuid.uuid4())
    return response_detail


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
