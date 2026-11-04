import json
import os

import pytest
from fastapi.testclient import TestClient

from app.config import settings


@pytest.fixture(autouse=True)
def fresh_data_file():
    data = {
        "patient": {"id": "patient-1", "name": "Jane Patient", "phone_number": "+15555550123"},
        "staff": {"id": "staff-1", "name": "Dr. Smith"},
        "calls": [],
    }
    os.makedirs(os.path.dirname(settings.DATA_FILE) or ".", exist_ok=True)
    with open(settings.DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)
    yield
    if os.path.exists(settings.DATA_FILE):
        os.remove(settings.DATA_FILE)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("app.routers.voice.validate_twilio_signature", lambda *a, **k: True)
    monkeypatch.setattr("app.routers.webhooks.validate_twilio_signature", lambda *a, **k: True)
    from app.main import app

    return TestClient(app)


def test_voice_outbound_returns_twiml_for_valid_phone_number(client):
    response = client.post(
        "/voice/outbound",
        data={"phone_number": "+15555550123", "CallSid": "CA123"},
    )
    assert response.status_code == 200
    assert "<Dial" in response.text
    assert "+15555550123" in response.text


def test_voice_outbound_rejects_malformed_phone_number(client):
    response = client.post(
        "/voice/outbound",
        data={"phone_number": "not-a-number", "CallSid": "CA123"},
    )
    assert response.status_code == 400


def test_recording_webhook_triggers_transcription_once(client, monkeypatch):
    from app import storage

    storage.create_call(patient_id="patient-1", staff_id="staff-1")
    storage.set_twilio_call_sid(storage.list_calls_for_patient("patient-1")[0]["id"], "CA999")

    called = {"count": 0}

    def fake_transcribe_and_save(call_id, recording_url):
        called["count"] += 1

    monkeypatch.setattr("app.routers.webhooks._transcribe_and_save", fake_transcribe_and_save)

    payload = {
        "CallSid": "CA999",
        "RecordingSid": "RE111",
        "RecordingUrl": "https://api.twilio.com/recordings/RE111",
    }

    r1 = client.post("/webhooks/recording", data=payload)
    assert r1.status_code == 200

    # duplicate callback should be ignored (idempotency)
    r2 = client.post("/webhooks/recording", data=payload)
    assert r2.status_code == 200

    call = storage.get_call_by_recording_sid("RE111")
    assert call is not None
    assert call["recording_url"] == payload["RecordingUrl"]
