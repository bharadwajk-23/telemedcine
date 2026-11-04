"""Tiny JSON-file storage layer. Good enough for a single-patient demo."""
import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()

_DEFAULT_DATA = {
    "patient": {
        "id": "patient-1",
        "name": "Jane Patient",
        "phone_number": "+15555550123",
    },
    "staff": {
        "id": "staff-1",
        "name": "Dr. Smith",
    },
    "calls": [],
}


def _ensure_file() -> None:
    os.makedirs(os.path.dirname(settings.DATA_FILE) or ".", exist_ok=True)
    if not os.path.exists(settings.DATA_FILE):
        with open(settings.DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(_DEFAULT_DATA, f, indent=2)


def _read() -> dict:
    _ensure_file()
    with open(settings.DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _write(data: dict) -> None:
    with open(settings.DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def get_patient() -> dict:
    with _lock:
        return _read()["patient"]


def get_staff() -> dict:
    with _lock:
        return _read()["staff"]


def create_call(patient_id: str, staff_id: str) -> dict:
    with _lock:
        data = _read()
        call = {
            "id": str(uuid.uuid4()),
            "patient_id": patient_id,
            "staff_id": staff_id,
            "twilio_call_sid": None,
            "status": "initiated",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": None,
            "duration_seconds": None,
            "recording_sid": None,
            "recording_url": None,
            "dialed_phone": None,
        }
        data["calls"].append(call)
        _write(data)
        return call


def get_call(call_id: str) -> Optional[dict]:
    with _lock:
        data = _read()
    for call in data["calls"]:
        if call["id"] == call_id:
            return call
    return None


def get_call_by_sid(call_sid: str) -> Optional[dict]:
    with _lock:
        data = _read()
    for call in data["calls"]:
        if call["twilio_call_sid"] == call_sid:
            return call
    return None


def get_call_by_recording_sid(recording_sid: str) -> Optional[dict]:
    with _lock:
        data = _read()
    for call in data["calls"]:
        if call["recording_sid"] == recording_sid:
            return call
    return None


def list_calls_for_patient(patient_id: str) -> list:
    with _lock:
        data = _read()
    return [c for c in data["calls"] if c["patient_id"] == patient_id]


def update_call(call_id: str, **fields: Any) -> Optional[dict]:
    with _lock:
        data = _read()
        for call in data["calls"]:
            if call["id"] == call_id:
                call.update(fields)
                _write(data)
                return call
    return None


def set_twilio_call_sid(call_id: str, call_sid: str) -> None:
    update_call(call_id, twilio_call_sid=call_sid)
