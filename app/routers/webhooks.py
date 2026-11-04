"""Twilio status/recording webhooks."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import Response

from app import storage
from app.config import settings
from app.services.twilio_service import validate_twilio_signature

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhooks/call-status")
async def call_status(request: Request, x_twilio_signature: str = Header(default="")):
    form = await request.form()
    params = dict(form)

    url = f"{settings.BASE_URL}/webhooks/call-status"
    if not validate_twilio_signature(url, params, x_twilio_signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    call_sid = params.get("CallSid")
    call_status_value = params.get("CallStatus")
    duration = params.get("CallDuration")

    call = storage.get_call_by_sid(call_sid)
    if not call:
        logger.warning("call-status webhook for unknown CallSid")
        return Response(status_code=200)

    fields = {"status": call_status_value}
    if duration is not None:
        fields["duration_seconds"] = int(duration)
    if call_status_value == "completed":
        fields["ended_at"] = datetime.now(timezone.utc).isoformat()

    storage.update_call(call["id"], **fields)
    return Response(status_code=200)


@router.post("/webhooks/recording")
async def recording_complete(request: Request, x_twilio_signature: str = Header(default="")):
    """Twilio calls this when the dual-channel recording is ready.

    No transcription step - the recording itself (accessible via its Twilio
    recording_url, authenticated with your account credentials) is the result.
    """
    form = await request.form()
    params = dict(form)

    url = f"{settings.BASE_URL}/webhooks/recording"
    if not validate_twilio_signature(url, params, x_twilio_signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    call_sid = params.get("CallSid")
    recording_sid = params.get("RecordingSid")
    recording_url = params.get("RecordingUrl")

    if not recording_sid:
        raise HTTPException(status_code=400, detail="Missing RecordingSid")

    # Idempotency: ignore duplicate callbacks for the same recording.
    existing = storage.get_call_by_recording_sid(recording_sid)
    if existing:
        logger.info("Duplicate recording callback for %s, ignoring", recording_sid)
        return Response(status_code=200)

    call = storage.get_call_by_sid(call_sid)
    if not call:
        logger.warning("recording webhook for unknown CallSid")
        return Response(status_code=200)

    storage.update_call(call["id"], recording_sid=recording_sid, recording_url=recording_url)

    return Response(status_code=200)
