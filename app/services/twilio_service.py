"""Thin wrapper around Twilio: access tokens, TwiML generation, signature
validation and recording download."""
import logging
import re

import httpx
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import Dial, Number, VoiceResponse

from app.config import settings

logger = logging.getLogger(__name__)

CONSENT_MESSAGE = (
    "This call may be recorded and transcribed for medical record purposes."
)

E164_PATTERN = re.compile(r"^\+[1-9]\d{6,14}$")


def is_valid_e164(phone_number: str) -> bool:
    """Validate that a phone number is a well-formed E.164 number.

    This is a format check only, not a trust boundary: the caller is still
    responsible for deciding whether this number is safe to dial.
    """
    return bool(phone_number) and bool(E164_PATTERN.match(phone_number))


def mask_phone(phone_number: str) -> str:
    """Mask all but the last 2 digits of a phone number for safe logging."""
    if not phone_number or len(phone_number) < 4:
        return "***"
    return "*" * (len(phone_number) - 2) + phone_number[-2:]


def create_access_token(identity: str) -> str:
    """Create a short-lived Twilio Voice access token for the browser softphone."""
    token = AccessToken(
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_API_KEY,
        settings.TWILIO_API_SECRET,
        identity=identity,
        ttl=3600,
    )
    voice_grant = VoiceGrant(
        outgoing_application_sid=settings.TWILIO_TWIML_APP_SID,
        incoming_allow=True,
    )
    token.add_grant(voice_grant)
    return token.to_jwt()


def build_outbound_twiml(patient_phone: str) -> str:
    """Build TwiML that announces consent then dials the patient, dual-channel recorded."""
    response = VoiceResponse()
    response.say(CONSENT_MESSAGE)

    dial = Dial(
        caller_id=settings.TWILIO_CALLER_ID,
        record="record-from-answer-dual",
        recording_status_callback=f"{settings.BASE_URL}/webhooks/recording",
        recording_status_callback_event="completed",
    )
    dial.append(Number(patient_phone))
    response.append(dial)
    return str(response)


def validate_twilio_signature(url: str, form_params: dict, signature: str) -> bool:
    """Validate the X-Twilio-Signature header on an incoming webhook request."""
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    return validator.validate(url, form_params, signature)


async def download_recording(recording_url: str) -> bytes:
    """Download a recording from Twilio using account credentials."""
    url = recording_url if recording_url.endswith(".wav") else f"{recording_url}.wav"
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
            timeout=30.0,
        )
        response.raise_for_status()
        return response.content
