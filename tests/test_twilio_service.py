from app.services.twilio_service import build_outbound_twiml, is_valid_e164, mask_phone


def test_build_outbound_twiml_includes_consent_and_dial():
    twiml = build_outbound_twiml("+15551234567")

    assert "recorded" in twiml
    assert "<Dial" in twiml
    assert "record=\"record-from-answer-dual\"" in twiml
    assert "<Number>+15551234567</Number>" in twiml
    assert "/webhooks/recording" in twiml


def test_mask_phone_hides_all_but_last_two_digits():
    assert mask_phone("+15551234567") == "**********67"
    assert mask_phone("12") == "***"


def test_is_valid_e164():
    assert is_valid_e164("+15551234567") is True
    assert is_valid_e164("5551234567") is False
    assert is_valid_e164("not-a-number") is False
    assert is_valid_e164("") is False
    assert is_valid_e164(None) is False
