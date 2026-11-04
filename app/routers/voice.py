"""Twilio voice webhook: turns a browser softphone call into a real PSTN dial."""
import logging

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import Response

from app import storage
from app.config import settings
from app.services.twilio_service import (
    build_outbound_twiml,
    is_valid_e164,
    mask_phone,
    validate_twilio_signature,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/voice/outbound")
async def voice_outbound(request: Request, x_twilio_signature: str = Header(default="")):
    """Twilio calls this when the browser softphone places an outgoing call.

    The number to dial comes from the browser (phone_number param) rather than
    a patient lookup. It is only format-validated (E.164) here - the caller
    (staff member) is trusted to have typed the right number, same as dialing
    a number on a normal office phone.
    """
    form = await request.form()
    params = dict(form)

    url = f"{settings.BASE_URL}/voice/outbound"
    if not validate_twilio_signature(url, params, x_twilio_signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    phone_number = params.get("phone_number")
    call_sid = params.get("CallSid")
    staff_id = params.get("staff_id") or storage.get_staff()["id"]

    if not is_valid_e164(phone_number):
        logger.warning("Rejected outbound call request with malformed phone number")
        raise HTTPException(status_code=400, detail="phone_number must be a valid E.164 number")

    patient = storage.get_patient()
    call = storage.create_call(patient_id=patient["id"], staff_id=staff_id)
    storage.set_twilio_call_sid(call["id"], call_sid)
    storage.update_call(call["id"], dialed_phone=phone_number)

    logger.info("Outbound call %s to %s", call_sid, mask_phone(phone_number))

    twiml = build_outbound_twiml(phone_number)
    return Response(content=twiml, media_type="application/xml")
