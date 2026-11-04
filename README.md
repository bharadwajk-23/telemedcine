# Telemedicine Click-to-Call (Quick Starter)

A minimal working demo: a staff member calls a patient's real phone number from a
browser softphone, and the call is recorded in dual-channel (staff on one
track, patient on the other). No transcription — just the recording.

This is a **quick starter, not production-ready**: no authentication, a single
hardcoded patient and staff user, and JSON-file storage (`data/data.json`)
instead of a database. See "Compliance notes" below before using with real
patient data.

## Project structure

```
app/
  main.py                      FastAPI app + static file serving
  config.py                    Settings from .env
  storage.py                   JSON-file storage (patient, staff, calls)
  routers/
    token.py                   GET /api/token
    voice.py                   POST /voice/outbound (Twilio webhook)
    webhooks.py                POST /webhooks/call-status, /webhooks/recording
    calls.py                   GET /api/patients, /api/patients/{id}/calls, /api/calls/{id}
  services/
    twilio_service.py          Access tokens, TwiML, signature validation
  static/
    index.html, softphone.js   Demo page (Twilio Voice JS SDK)
data/data.json                 Seeded with 1 patient + 1 staff user; calls appended here
tests/                         pytest tests (TwiML + webhook handler, Twilio mocked)
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
4. Answer the call on the patient's phone (use your own phone number to test).
5. Hang up. Twilio posts the finished recording to `/webhooks/recording`,
   which just stores the recording's SID and URL against the call.
6. Click **Refresh recording status** on the demo page once the call ends.
   An audio player appears and plays the recording directly in the page -
   `GET /api/calls/{call_id}/recording` proxies the audio from Twilio
   server-side (using your Account SID/Auth Token), so the browser never
   needs Twilio credentials.

## Seed data / editing the patient

Edit `data/data.json` directly to change the patient's phone number (must be
E.164, e.g. `+15551234567`) or staff name. The file is auto-created with
defaults on first run if missing.

## Running tests

```bash
pytest
```

Tests mock Twilio signature validation and cover TwiML generation plus the
recording webhook's idempotency (duplicate `RecordingSid` callbacks are
ignored).

## Compliance notes (read before real use)

- **Consent**: the call plays a spoken consent announcement before dialing.
  For real use, also log a persistent consent record per call (not just the
  announcement).
- **HIPAA (US)**: you need a signed Business Associate Agreement (BAA) with
  Twilio before processing real patient data.
- **DPDP Act (India)**: data residency and explicit consent requirements
  apply to patient voice data.
- **Encryption & access control**: recordings should be encrypted at rest and
  access-controlled. This starter stores only metadata (SID/URL) in a plain
  JSON file with no encryption — fine for a local demo, not for real patient
  data. The actual audio stays in your Twilio account.
- **Retention**: add a configurable retention period and a scheduled job that
  calls Twilio's API to delete recordings past that period. Not implemented
  in this starter.
- **Phone numbers in logs**: `twilio_service.mask_phone()` masks all but the
  last 2 digits; logs never include full phone numbers.
- **Trusted dialer input**: the demo page lets staff type any phone number to
  call, and `/voice/outbound` only checks that it's well-formed E.164 (see
  `is_valid_e164` in `twilio_service.py`) — it does not verify the number
  belongs to a specific patient record. This is fine for a single
  trusted-staff demo; for real multi-patient use, go back to looking the
  number up server-side from a `patient_id` so a compromised or malicious
  browser can't dial arbitrary numbers through your Twilio account.

## Adding transcription later

If you want speech-to-text later, add a service that downloads the recording
(`recording_url` + your Twilio Account SID/Auth Token for auth) in the
`/webhooks/recording` handler and sends it to any STT provider (Deepgram,
AssemblyAI, AWS Transcribe, OpenAI, etc. — see the pricing comparison doc
from this project's chat history for options and costs).

## Swapping in a real database / auth later

- `app/storage.py` is the only place that knows about JSON files — replace
  its functions with SQLAlchemy models/queries to move to Postgres without
  touching the routers.
- Add a `get_current_staff` FastAPI dependency and wire it into
  `routers/token.py` and `routers/voice.py` in place of the hardcoded
  single staff user.
