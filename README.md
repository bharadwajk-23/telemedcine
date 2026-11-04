# Telemedicine Click-to-Call (Quick Starter)

A minimal working demo: a staff member calls a patient's real phone number from a
browser softphone, the call is recorded in dual-channel, and the recording is
transcribed with speaker labels (staff vs. patient).

This is a **quick starter, not production-ready**: no authentication, a single
hardcoded patient and staff user, and JSON-file storage (`data/data.json`)
instead of a database. See "Compliance notes" below before using with real
patient data.

## Project structure

```
app/
  main.py                      FastAPI app + static file serving
  config.py                    Settings from .env
  storage.py                   JSON-file storage (patient, staff, calls, transcripts)
  routers/
    token.py                   GET /api/token
    voice.py                   POST /voice/outbound (Twilio webhook)
    webhooks.py                POST /webhooks/call-status, /webhooks/recording
    calls.py                   GET /api/patients, /api/patients/{id}/calls, /api/calls/{id}/transcript
  services/
    twilio_service.py          Access tokens, TwiML, signature validation, recording download
    transcription_service.py   Deepgram transcription with retries
  static/
    index.html, softphone.js   Demo page (Twilio Voice JS SDK)
data/data.json                 Seeded with 1 patient + 1 staff user; calls appended here
tests/                         pytest tests (TwiML + webhook handler, Twilio/Deepgram mocked)
```

## 1. Install

```bash
pip install -r requirements.txt
```

## 2. Configure

```bash
cp .env.example .env
```

Fill in:
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` — from the Twilio Console.
- `TWILIO_API_KEY` / `TWILIO_API_SECRET` — create an API key at
  Console > Account > API keys & tokens.
- `TWILIO_CALLER_ID` — a Twilio phone number you own (shown as caller ID to the patient).
- `TWILIO_TWIML_APP_SID` — see step 3.
- `DEEPGRAM_API_KEY` — from the Deepgram console.
- `BASE_URL` — your public ngrok URL (step 4), e.g. `https://abcd1234.ngrok-free.app`.

## 3. Create a Twilio TwiML App

In the Twilio Console: Voice > TwiML Apps > Create new TwiML App.
- Voice Request URL: `{BASE_URL}/voice/outbound` (HTTP POST)
- Call Status Changes webhook (optional, under your Twilio number config or
  Dial's `statusCallback` if you extend it): `{BASE_URL}/webhooks/call-status`

Copy the TwiML App SID into `TWILIO_TWIML_APP_SID`.

## 4. Expose localhost with ngrok (for Twilio webhooks)

```bash
ngrok http 8000
```

Copy the `https://*.ngrok-free.app` URL into `BASE_URL` in `.env`, and update
the TwiML App's Voice Request URL to `{BASE_URL}/voice/outbound` whenever the
ngrok URL changes (free ngrok URLs change on every restart).

## 5. Run

```bash
uvicorn app.main:app --reload
```

Open `http://localhost:8000` (not the ngrok URL — the demo page itself doesn't
need to be public, only the webhook endpoints Twilio calls do).

## 6. Test the full flow end to end

1. Open `http://localhost:8000`. The softphone registers using `/api/token`.
2. The phone number field is pre-filled with the seeded patient's number from
   `data/data.json`, but you can type any E.164 number to call. Click **Call**.
3. The browser connects via WebRTC; Twilio hits `{BASE_URL}/voice/outbound`,
   which validates the number's format (E.164) and returns TwiML that plays a
   consent announcement, then dials it with dual-channel recording.
4. Answer the call on the patient's phone (use your own phone number as the
   seeded patient to test, or edit `data/data.json`).
5. Hang up. Twilio posts the finished recording to
   `/webhooks/recording`, which downloads the audio and kicks off a Deepgram
   transcription in the background.
6. Click **Refresh transcript** on the demo page (or
   `GET /api/calls/{call_id}/transcript`) after a few seconds to see the
   speaker-labelled transcript.

## Seed data / editing the patient

Edit `data/data.json` directly to change the patient's phone number (must be
E.164, e.g. `+15551234567`) or staff name. The file is auto-created with
defaults on first run if missing.

## Running tests

```bash
pytest
```

Tests mock Twilio signature validation and Deepgram, and cover TwiML
generation and the recording webhook's idempotency (duplicate
`RecordingSid` callbacks are ignored).

## Compliance notes (read before real use)

- **Consent**: the call plays a spoken consent announcement before dialing.
  For real use, also log a persistent consent record per call (not just the
  announcement).
- **HIPAA (US)**: you need a signed Business Associate Agreement (BAA) with
  both Twilio and Deepgram before processing real patient data.
- **DPDP Act (India)**: data residency and explicit consent requirements
  apply to patient voice/transcript data.
- **Encryption & access control**: recordings and transcripts should be
  encrypted at rest and access-controlled. This starter stores everything in
  a plain JSON file with no encryption — fine for a local demo, not for real
  patient data.
- **Retention**: add a configurable retention period and a scheduled job that
  deletes recordings/transcripts (and calls Twilio's API to delete the
  recording) past that period. Not implemented in this starter.
- **Phone numbers in logs**: `twilio_service.mask_phone()` masks all but the
  last 2 digits; logs never include full phone numbers or transcript text.
- **Trusted dialer input**: the demo page lets staff type any phone number to
  call, and `/voice/outbound` only checks that it's well-formed E.164 (see
  `is_valid_e164` in `twilio_service.py`) — it does not verify the number
  belongs to a specific patient record. This is fine for a single
  trusted-staff demo; for real multi-patient use, go back to looking the
  number up server-side from a `patient_id` so a compromised or malicious
  browser can't dial arbitrary numbers through your Twilio account.

## Swapping in a real database / auth later

- `app/storage.py` is the only place that knows about JSON files — replace
  its functions with SQLAlchemy models/queries to move to Postgres without
  touching the routers.
- Add a `get_current_staff` FastAPI dependency and wire it into
  `routers/token.py` and `routers/voice.py` in place of the hardcoded
  single staff user.
