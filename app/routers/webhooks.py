"""Twilio status/recording webhooks."""
import logging

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from fastapi.responses import Response

from app import storage
from app.config import settings
from app.services.transcription_service import transcribe_recording
from app.services.twilio_service import download_recording, validate_twilio_signature

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
        from datetime import datetime, timezone

        fields["ended_at"] = datetime.now(timezone.utc).isoformat()

    storage.update_call(call["id"], **fields)
    return Response(status_code=200)


@router.post("/webhooks/recording")
async def recording_complete(
    request: Request,
    background_tasks: BackgroundTasks,
    x_twilio_signature: str = Header(default=""),
):
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
    storage.set_transcript(call["id"], status="pending")

    background_tasks.add_task(_transcribe_and_save, call["id"], recording_url)

    return Response(status_code=200)


def _transcribe_and_save(call_id: str, recording_url: str) -> None:
    """Background task: download recording, transcribe, save result."""
    import asyncio

    from datetime import datetime, timezone

    try:
        audio_bytes = asyncio.run(download_recording(recording_url))
        result = transcribe_recording(audio_bytes)
        storage.set_transcript(
            call_id,
            status="done",
            full_text=result["full_text"],
            utterances=result["utterances"],
            language=result["language"],
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        logger.info("Transcript ready for call %s", call_id)
    except Exception:  # noqa: BLE001
        logger.exception("Transcription failed for call %s", call_id)
        storage.set_transcript(call_id, status="failed")
