"""Access token endpoint for the browser softphone."""
import logging

from fastapi import APIRouter

from app import storage
from app.services.twilio_service import create_access_token

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/token")
def get_token():
    """Return a Twilio Voice access token for the (single, hardcoded) staff user."""
    staff = storage.get_staff()
    token = create_access_token(identity=staff["id"])
    return {"token": token, "identity": staff["id"]}
