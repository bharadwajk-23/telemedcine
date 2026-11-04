"""Deepgram transcription with speaker (channel) labelling for phone calls."""
import logging
import time
from typing import Optional

from deepgram import DeepgramClient, FileSource, PrerecordedOptions

from app.config import settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2

# channel 0 = first <Number> leg = patient (callee), channel 1 = caller (staff)
CHANNEL_SPEAKER_MAP = {0: "patient", 1: "staff"}


def transcribe_recording(audio_bytes: bytes) -> dict:
    """Send audio to Deepgram and return {full_text, utterances, language}.

    Retries up to MAX_RETRIES times on failure. Raises the last exception if
    all attempts fail, so the caller can mark the transcript as failed.
    """
    client = DeepgramClient(settings.DEEPGRAM_API_KEY)
    payload: FileSource = {"buffer": audio_bytes}
    options = PrerecordedOptions(
        model="nova-2-phonecall",
        diarize=True,
        utterances=True,
        punctuate=True,
        smart_format=True,
        multichannel=True,
    )

    last_error: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.listen.rest.v("1").transcribe_file(payload, options)
            return _parse_response(response)
        except Exception as exc:  # noqa: BLE001 - we want to retry any failure
            last_error = exc
            logger.warning("Deepgram transcription attempt %s/%s failed: %s", attempt, MAX_RETRIES, exc)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

    raise last_error  # type: ignore[misc]


def _parse_response(response) -> dict:
    result = response.to_dict() if hasattr(response, "to_dict") else response
    channels = result["results"]["channels"]

    utterances = []
    full_text_parts = []
    language = None

    for channel_index, channel in enumerate(channels):
        speaker = CHANNEL_SPEAKER_MAP.get(channel_index, f"channel_{channel_index}")
        alt = channel["alternatives"][0]
        language = alt.get("language", language)
        for utt in channel.get("utterances", alt.get("words", [])):
            text = utt.get("transcript") or utt.get("word", "")
            if not text:
                continue
            utterances.append(
                {
                    "speaker": speaker,
                    "start": utt.get("start"),
                    "end": utt.get("end"),
                    "text": text,
                }
            )
            full_text_parts.append(f"{speaker}: {text}")

    utterances.sort(key=lambda u: u["start"] or 0)
    full_text = "\n".join(full_text_parts)

    return {"full_text": full_text, "utterances": utterances, "language": language}
