"""Read endpoints for patients and calls."""
from fastapi import APIRouter, HTTPException, Response

from app import storage
from app.services.twilio_service import download_recording

router = APIRouter()


@router.get("/api/patients")
def list_patients():
    """Only one hardcoded patient in this starter."""
    return [storage.get_patient()]


@router.get("/api/patients/{patient_id}/calls")
def list_calls(patient_id: str):
    return storage.list_calls_for_patient(patient_id)


@router.get("/api/calls/{call_id}")
def get_call(call_id: str):
    call = storage.get_call(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


@router.get("/api/calls/{call_id}/recording")
async def get_recording_audio(call_id: str):
    """Proxy a call's recording audio from Twilio so the browser never needs
    Twilio credentials - lets the demo page play it with a plain <audio> tag."""
    call = storage.get_call(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    if not call.get("recording_url"):
        raise HTTPException(status_code=404, detail="No recording for this call yet")

    audio_bytes = await download_recording(call["recording_url"])
    return Response(content=audio_bytes, media_type="audio/mpeg")
